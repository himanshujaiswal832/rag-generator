"""
RAG Application Instance - Isolated, Stateful RAG Pipeline
"""

import os
import time
import json
from typing import List, Dict, Any, Optional, Tuple

from rag_generator.core.models import (
    Document,
    Chunk,
    Citation,
    GroundedAnswer,
    RAGAppConfig,
    RAGAppMetadata,
    QueryRequest,
)
from rag_generator.ingestion.pipeline import IngestionPipeline
from rag_generator.indexing.embeddings import get_embedding_provider
from rag_generator.indexing.vector_store import VectorStore
from rag_generator.indexing.bm25_index import BM25Index
from rag_generator.indexing.hybrid_retriever import HybridRetriever
from rag_generator.generation.generator import AnswerGenerator
from rag_generator.generation.llm_provider import get_llm_provider


class RAGApplicationInstance:
    """An isolated, runnable RAG application with dedicated indices and configuration."""

    def __init__(self, config: RAGAppConfig, storage_dir: Optional[str] = None):
        self.config = config
        self.storage_dir = storage_dir
        self.app_id = config.app_id or "default-app"

        # Ingestion pipeline
        self.ingestion_pipeline = IngestionPipeline(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

        # Indexing components
        self.embedder = get_embedding_provider(model_name=config.embedding_model)
        self.vector_store = VectorStore(embedder=self.embedder)
        self.bm25_index = BM25Index()
        self.hybrid_retriever = HybridRetriever(
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            default_alpha=config.hybrid_alpha,
        )

        # Generation components
        self.llm_provider = get_llm_provider(
            provider_name=config.llm_provider,
            model_name=config.model_name,
        )
        self.answer_generator = AnswerGenerator(default_provider=self.llm_provider)

        # In-memory document registry
        self.documents: Dict[str, Document] = {}
        self.created_at = config.created_at
        self.updated_at = config.created_at

    def add_document(self, doc: Document, chunks: List[Chunk]) -> None:
        """Register document and update vector and BM25 indices."""
        self.documents[doc.document_id] = doc
        self.vector_store.add_chunks(chunks)
        self.bm25_index.add_chunks(chunks)
        self.updated_at = time.time()
        if self.storage_dir:
            self.save_to_disk()

    def ingest_file(self, file_path: str) -> Tuple[Document, int]:
        """Ingest a single file from the filesystem."""
        doc, chunks = self.ingestion_pipeline.process_file(file_path)
        self.add_document(doc, chunks)
        return doc, len(chunks)

    def ingest_bytes(self, file_bytes: bytes, filename: str, file_type: str = "text") -> Tuple[Document, int]:
        """Ingest in-memory file bytes (e.g. from web upload)."""
        doc, chunks = self.ingestion_pipeline.process_bytes(
            file_bytes=file_bytes,
            filename=filename,
            file_type=file_type,
        )
        self.add_document(doc, chunks)
        return doc, len(chunks)

    def ingest_raw_text(self, text: str, title: str = "Note.txt") -> Tuple[Document, int]:
        """Ingest raw string content."""
        doc, chunks = self.ingestion_pipeline.process_raw_text(text=text, title=title)
        self.add_document(doc, chunks)
        return doc, len(chunks)

    def query(self, req: QueryRequest) -> GroundedAnswer:
        """Execute hybrid retrieval and generate a verified grounded answer."""
        start_retrieval = time.time()

        top_k = req.top_k or self.config.top_k
        alpha = req.hybrid_alpha if req.hybrid_alpha is not None else self.config.hybrid_alpha
        min_relevance = req.min_relevance if req.min_relevance is not None else self.config.similarity_threshold

        # Execute hybrid retrieval
        retrieved_results = self.hybrid_retriever.retrieve(
            query=req.question,
            top_k=top_k,
            alpha=alpha,
            min_relevance=min_relevance,
        )

        retrieval_latency_ms = (time.time() - start_retrieval) * 1000.0

        # Determine dynamic LLM provider if requested
        provider = self.llm_provider
        if req.llm_provider and (req.llm_provider != self.config.llm_provider or req.api_key):
            provider = get_llm_provider(
                provider_name=req.llm_provider,
                api_key=req.api_key,
                model_name=req.model_name,
                api_base=req.api_base,
            )

        # Generate answer with grounding verification
        answer = self.answer_generator.generate_grounded_answer(
            question=req.question,
            retrieved_results=retrieved_results,
            llm_provider=provider,
            min_relevance_threshold=min_relevance,
            temperature=req.temperature or 0.1,
            retrieval_latency_ms=retrieval_latency_ms,
        )

        return answer

    def get_metadata(self) -> RAGAppMetadata:
        """Return application summary stats and metadata."""
        docs_summary = []
        total_chars = 0
        file_types = set()

        for d in self.documents.values():
            docs_summary.append({
                "document_id": d.document_id,
                "filename": d.filename,
                "file_type": d.file_type,
                "char_count": d.char_count,
                "token_estimate": d.token_estimate,
                "page_count": d.metadata.get("page_count", 1),
                "created_at": d.created_at,
            })
            total_chars += d.char_count
            file_types.add(d.file_type)

        return RAGAppMetadata(
            app_id=self.app_id,
            name=self.config.name,
            description=self.config.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
            document_count=len(self.documents),
            chunk_count=self.vector_store.count(),
            total_characters=total_chars,
            total_tokens_estimate=total_chars // 4,
            file_types=sorted(list(file_types)),
            documents=docs_summary,
            config=self.config,
        )

    def get_chunks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return all or first N chunks for data inspection."""
        return [c.to_dict() for c in self.vector_store.chunks[:limit]]

    def save_to_disk(self) -> None:
        """Persist application data, config, and indices to directory."""
        if not self.storage_dir:
            return

        app_dir = os.path.join(self.storage_dir, self.app_id)
        os.makedirs(app_dir, exist_ok=True)

        # Save config
        config_path = os.path.join(app_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self.config.model_dump_json(indent=2))

        # Save documents
        docs_path = os.path.join(app_dir, "documents.json")
        docs_data = {doc_id: d.model_dump() for doc_id, d in self.documents.items()}
        with open(docs_path, "w", encoding="utf-8") as f:
            json.dump(docs_data, f, indent=2)

        # Save vector store & chunks
        self.vector_store.save_to_disk(app_dir)

    @classmethod
    def load_from_disk(cls, app_dir: str, storage_root: str) -> "RAGApplicationInstance":
        """Load an existing application from disk."""
        config_path = os.path.join(app_dir, "config.json")
        docs_path = os.path.join(app_dir, "documents.json")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Missing config.json in {app_dir}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        config = RAGAppConfig(**config_data)
        instance = cls(config=config, storage_dir=storage_root)

        # Load documents
        if os.path.exists(docs_path):
            with open(docs_path, "r", encoding="utf-8") as f:
                docs_dict = json.load(f)
            instance.documents = {k: Document(**v) for k, v in docs_dict.items()}

        # Load vector store
        instance.vector_store.load_from_disk(app_dir)

        # Refit TF-IDF vocabulary if using TFIDFEmbedder
        if hasattr(instance.embedder, "fit_and_embed") and instance.vector_store.chunks:
            texts = [c.content for c in instance.vector_store.chunks]
            instance.embedder.fit_and_embed(texts)

        # Rebuild BM25 index from loaded chunks
        instance.bm25_index.add_chunks(instance.vector_store.chunks)

        return instance
