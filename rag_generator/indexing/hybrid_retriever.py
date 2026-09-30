"""
Hybrid Retriever combining Dense Vector and Sparse BM25 Search via Reciprocal Rank Fusion (RRF)
"""

from typing import List, Tuple, Dict, Any, Optional
from rag_generator.core.models import Chunk
from rag_generator.indexing.vector_store import VectorStore
from rag_generator.indexing.bm25_index import BM25Index


class HybridRetriever:
    """Orchestrates hybrid dense + sparse retrieval with Reciprocal Rank Fusion."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        default_alpha: float = 0.5,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.default_alpha = default_alpha
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        alpha: Optional[float] = None,
        min_relevance: float = 0.15,
    ) -> List[Tuple[Chunk, float, Dict[str, Any]]]:
        """
        Execute hybrid search and return ranked (Chunk, fused_score, debug_details).
        
        Args:
            query: The user query string.
            top_k: Maximum number of chunks to return.
            alpha: Weight for dense search (0.0 = BM25 only, 1.0 = Dense only).
            min_relevance: Minimum acceptable fused relevance threshold.
        """
        if alpha is None:
            alpha = self.default_alpha

        # Fetch more candidates for fusion
        candidate_k = max(top_k * 3, 15)

        dense_results = self.vector_store.search(query, top_k=candidate_k)
        bm25_results = self.bm25_index.search(query, top_k=candidate_k)

        # Build rank maps
        dense_ranks: Dict[str, Tuple[int, float, Chunk]] = {}
        for rank, (chunk, score) in enumerate(dense_results, 1):
            dense_ranks[chunk.chunk_id] = (rank, score, chunk)

        bm25_ranks: Dict[str, Tuple[int, float, Chunk]] = {}
        for rank, (chunk, score) in enumerate(bm25_results, 1):
            bm25_ranks[chunk.chunk_id] = (rank, score, chunk)

        # Collect all unique chunk IDs
        all_chunk_ids = set(dense_ranks.keys()).union(set(bm25_ranks.keys()))
        if not all_chunk_ids:
            return []

        scored_candidates = []
        for c_id in all_chunk_ids:
            # Dense component
            if c_id in dense_ranks:
                d_rank, d_score, chunk = dense_ranks[c_id]
                dense_rrf = 1.0 / (self.rrf_k + d_rank)
            else:
                d_score = 0.0
                dense_rrf = 0.0
                chunk = bm25_ranks[c_id][2]

            # BM25 component
            if c_id in bm25_ranks:
                b_rank, b_score, _ = bm25_ranks[c_id]
                bm25_rrf = 1.0 / (self.rrf_k + b_rank)
            else:
                b_score = 0.0
                bm25_rrf = 0.0

            # Combined Reciprocal Rank Fusion score
            fused_rrf = (alpha * dense_rrf) + ((1.0 - alpha) * bm25_rrf)

            # Direct weighted score for intuitive 0.0 - 1.0 confidence display
            normalized_score = (alpha * d_score) + ((1.0 - alpha) * b_score)

            # Scale fused score for display
            display_score = max(normalized_score, fused_rrf * 40.0)
            display_score = min(1.0, max(0.0, display_score))

            details = {
                "dense_score": round(d_score, 4),
                "bm25_score": round(b_score, 4),
                "fused_rrf": round(fused_rrf, 5),
                "alpha": alpha,
            }

            if display_score >= min_relevance:
                scored_candidates.append((chunk, display_score, details))

        # Sort by fused score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates[:top_k]
