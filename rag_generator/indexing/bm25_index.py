"""
Sparse Lexical BM25 Index for High-Precision Keyword Retrieval
"""

import re
from typing import List, Tuple, Optional
from rank_bm25 import BM25Okapi
from rag_generator.core.models import Chunk


class BM25Index:
    """Okapi BM25 Index for lexical search over chunked documents."""

    def __init__(self):
        self.chunks: List[Chunk] = []
        self.tokenized_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Normalize and tokenize text into clean word tokens."""
        text = text.lower()
        # Keep alphanumeric words and common acronyms / hyphenated terms
        tokens = re.findall(r"\b[a-z0-9_-]+\b", text)
        return tokens

    def add_chunks(self, new_chunks: List[Chunk]) -> int:
        """Add chunks and rebuild the BM25 index."""
        if not new_chunks:
            return 0

        self.chunks.extend(new_chunks)
        for chunk in new_chunks:
            tokens = self.tokenize(chunk.content)
            self.tokenized_corpus.append(tokens)

        if self.tokenized_corpus:
            self._bm25 = BM25Okapi(self.tokenized_corpus)

        return len(new_chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Tuple[Chunk, float]]:
        """Query the BM25 index and return ranked chunks with normalized scores."""
        if not self._bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        raw_scores = self._bm25.get_scores(query_tokens)
        max_score = max(raw_scores) if len(raw_scores) > 0 and max(raw_scores) > 0 else 1.0

        # Sort indices by score descending
        top_indices = sorted(range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            raw_s = raw_scores[idx]
            if raw_s <= 0:
                continue
            # Normalize to [0.0, 1.0]
            norm_score = float(raw_s / max_score)
            if norm_score >= min_score:
                results.append((self.chunks[idx], norm_score))

        return results

    def count(self) -> int:
        return len(self.chunks)
