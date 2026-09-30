"""
In-Memory Dense Vector Store with Cosine Similarity Matrix Search and File Persistence
"""

import os
import json
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from rag_generator.core.models import Chunk
from rag_generator.indexing.embeddings import BaseEmbedder


class VectorStore:
    """Stores chunk embeddings and executes fast vectorized cosine similarity search."""

    def __init__(self, embedder: BaseEmbedder):
        self.embedder = embedder
        self.chunks: List[Chunk] = []
        self.vectors: Optional[np.ndarray] = None  # Shape: (N, D)

    def add_chunks(self, new_chunks: List[Chunk]) -> int:
        """Embed and append new chunks to the vector store."""
        if not new_chunks:
            return 0

        texts = [c.content for c in new_chunks]
        new_vecs = self.embedder.embed_texts(texts)

        if self.vectors is None or len(self.vectors) == 0:
            self.vectors = new_vecs
        else:
            self.vectors = np.vstack([self.vectors, new_vecs])

        self.chunks.extend(new_chunks)
        return len(new_chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Tuple[Chunk, float]]:
        """Perform vectorized cosine similarity search."""
        if self.vectors is None or len(self.chunks) == 0:
            return []

        query_vec = self.embedder.embed_query(query)  # Shape: (D,)
        
        # Ensure query vector is unit normalized
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 1e-8:
            query_vec = query_vec / q_norm

        # Cosine similarity is dot product of normalized vectors
        scores = np.dot(self.vectors, query_vec)

        # Get top-k indices
        num_candidates = min(top_k, len(scores))
        if num_candidates == 0:
            return []

        # Argsort in descending order
        top_indices = np.argsort(scores)[::-1][:num_candidates]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= min_score:
                results.append((self.chunks[idx], score))

        return results

    def save_to_disk(self, directory: str) -> None:
        """Persist chunks and vector matrix to disk."""
        os.makedirs(directory, exist_ok=True)
        chunks_file = os.path.join(directory, "chunks.json")
        vectors_file = os.path.join(directory, "vectors.npy")

        # Serialize chunks
        serializable_chunks = [c.to_dict() for c in self.chunks]
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(serializable_chunks, f, indent=2)

        # Save numpy vectors
        if self.vectors is not None:
            np.save(vectors_file, self.vectors)
        else:
            np.save(vectors_file, np.empty((0, self.embedder.dimension), dtype=np.float32))

    def load_from_disk(self, directory: str) -> bool:
        """Load chunks and vector matrix from disk."""
        chunks_file = os.path.join(directory, "chunks.json")
        vectors_file = os.path.join(directory, "vectors.npy")

        if not os.path.exists(chunks_file) or not os.path.exists(vectors_file):
            return False

        with open(chunks_file, "r", encoding="utf-8") as f:
            raw_chunks = json.load(f)

        self.chunks = [Chunk(**data) for data in raw_chunks]
        self.vectors = np.load(vectors_file)
        return True

    def count(self) -> int:
        return len(self.chunks)
