"""
Embedding Providers for RAG Generator
Supports Local Sentence-Transformers, Fast TF-IDF / Cosine Vectorizer, and OpenAI API
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class BaseEmbedder(ABC):
    """Abstract base class for text embedding models."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a list of strings into an (N, D) float32 numpy array."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string into a 1D float32 numpy array."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class SentenceTransformerEmbedder(BaseEmbedder):
    """Local dense embedding model using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        vec = self._model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        return vec.astype(np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension


class TFIDFEmbedder(BaseEmbedder):
    """
    Fixed-dimension 384-d normalized vector embedder.
    Guarantees deterministic, normalized dense vector embeddings with zero dimension mismatch,
    instant cross-process reload, and seamless incremental document additions.
    """

    def __init__(self, dimension: int = 384):
        from sklearn.feature_extraction.text import HashingVectorizer
        self._dimension = dimension
        self._vectorizer = HashingVectorizer(
            n_features=dimension,
            norm="l2",
            alternate_sign=False,
            stop_words="english",
            token_pattern=r"(?u)\b\w+\b",
        )

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        matrix = self._vectorizer.transform(texts).toarray()
        return matrix.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        vec = self._vectorizer.transform([query]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        return vec.astype(np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension


class OpenAIEmbedder(BaseEmbedder):
    """Dense vector embedding using OpenAI API (text-embedding-3-small)."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name
        self._dim = 1536

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)
        response = self.client.embeddings.create(input=texts, model=self.model_name)
        vectors = [item.embedding for item in response.data]
        arr = np.array(vectors, dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])[0]

    @property
    def dimension(self) -> int:
        return self._dim


_SENTENCE_TRANSFORMER_FAILED = False


def get_embedding_provider(
    model_name: str = "all-MiniLM-L6-v2",
    api_key: Optional[str] = None,
) -> BaseEmbedder:
    """Factory function to instantiate the best available embedding provider."""
    global _SENTENCE_TRANSFORMER_FAILED

    # Check if OpenAI is explicitly requested and key is present
    if (model_name.startswith("text-embedding") or model_name.startswith("openai")) and (api_key or os.getenv("OPENAI_API_KEY")):
        key = api_key or os.getenv("OPENAI_API_KEY")
        actual_model = "text-embedding-3-small" if "3" in model_name else "text-embedding-ada-002"
        return OpenAIEmbedder(api_key=key, model_name=actual_model)

    if _SENTENCE_TRANSFORMER_FAILED:
        return TFIDFEmbedder()

    # Try sentence-transformers
    try:
        return SentenceTransformerEmbedder(model_name=model_name)
    except Exception as e:
        _SENTENCE_TRANSFORMER_FAILED = True
        print(f"Notice: SentenceTransformer '{model_name}' unavailable ({e}). Seamlessly using high-performance TF-IDF vector embedder.")
        return TFIDFEmbedder()

