"""
RAG Generator - Dynamic RAG Application Factory & Orchestration Engine
"""

__version__ = "1.0.0"
__author__ = "Candidate"

from rag_generator.core.models import (
    Document,
    Chunk,
    Citation,
    GroundedAnswer,
    RAGAppMetadata,
    RAGAppConfig,
    QueryRequest,
)
from rag_generator.core.factory import RAGFactory
from rag_generator.core.instance import RAGApplicationInstance

__all__ = [
    "Document",
    "Chunk",
    "Citation",
    "GroundedAnswer",
    "RAGAppMetadata",
    "RAGAppConfig",
    "QueryRequest",
    "RAGFactory",
    "RAGApplicationInstance",
]
