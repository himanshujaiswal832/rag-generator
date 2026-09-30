"""
Core Data Models for RAG Generator
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Represents an ingested document."""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pages: Optional[List[Dict[str, Any]]] = None
    created_at: float = Field(default_factory=time.time)

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def token_estimate(self) -> int:
        # Standard heuristic: 1 token ~ 4 chars for English text
        return max(1, len(self.content) // 4)


class Chunk(BaseModel):
    """Represents a discrete semantic chunk of a document."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    source_name: str
    content: str
    chunk_index: int
    page_number: Optional[int] = 1
    start_char: int = 0
    end_char: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Citation(BaseModel):
    """Represents an evidence citation backing a claim in a generated answer."""
    chunk_id: str
    document_id: str
    source_name: str
    page_number: Optional[int] = 1
    snippet: str
    relevance_score: float = 0.0
    text_match_excerpt: Optional[str] = None


class GroundedAnswer(BaseModel):
    """Structured response containing the grounded answer, citations, and evaluation metrics."""
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    groundedness_score: float = Field(
        default=1.0,
        description="Fraction of claims strictly supported by retrieved context (0.0 to 1.0)",
    )
    confidence: str = Field(
        default="High",
        description="Confidence label: High, Medium, Low, or Refusal",
    )
    context_coverage: float = Field(
        default=1.0,
        description="Estimated semantic overlap between query and retrieved passages",
    )
    retrieved_chunk_count: int = 0
    latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    model_used: str = "local_grounded_synthesizer"
    has_sufficient_context: bool = True
    refusal_reason: Optional[str] = None


class RAGAppConfig(BaseModel):
    """Configuration parameters for a generated RAG Application."""
    app_id: Optional[str] = None
    name: str = "Default RAG Application"
    description: str = "Auto-generated RAG Application"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 80
    hybrid_alpha: float = Field(
        default=0.5,
        description="Hybrid balance: 0.0 = Pure BM25 keyword search, 1.0 = Pure Dense vector search",
    )
    top_k: int = 4
    similarity_threshold: float = 0.20
    llm_provider: str = "local_grounded"
    model_name: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class RAGAppMetadata(BaseModel):
    """Summary metadata and health statistics for a generated RAG Application."""
    app_id: str
    name: str
    description: str
    created_at: float
    updated_at: float
    document_count: int = 0
    chunk_count: int = 0
    total_characters: int = 0
    total_tokens_estimate: int = 0
    file_types: List[str] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    config: RAGAppConfig


class QueryRequest(BaseModel):
    """Parameters passed to query an active RAG application."""
    question: str
    top_k: Optional[int] = None
    hybrid_alpha: Optional[float] = None
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    min_relevance: Optional[float] = None
    temperature: Optional[float] = 0.1
