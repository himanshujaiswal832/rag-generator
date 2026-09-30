"""
Unit Tests for Vector, BM25, and Hybrid Retrieval
"""

import pytest
from rag_generator.core.models import Chunk
from rag_generator.indexing.embeddings import TFIDFEmbedder
from rag_generator.indexing.vector_store import VectorStore
from rag_generator.indexing.bm25_index import BM25Index
from rag_generator.indexing.hybrid_retriever import HybridRetriever


@pytest.fixture
def sample_chunks():
    return [
        Chunk(
            document_id="doc1",
            source_name="quantum_specs.txt",
            content="The dilution refrigerator base temperature operates at 15 mK with HEMT amplifiers at 4K.",
            chunk_index=0,
            page_number=1,
        ),
        Chunk(
            document_id="doc2",
            source_name="saas_contract.txt",
            content="Customer SLA guarantees a 99.95% monthly uptime percentage with 25% credit for downtime.",
            chunk_index=1,
            page_number=1,
        ),
        Chunk(
            document_id="doc3",
            source_name="oncology_protocol.txt",
            content="TX-409 dosage is administered at 8.0 mg/kg intravenous infusion every 3 weeks (Q3W).",
            chunk_index=2,
            page_number=1,
        ),
    ]


def test_vector_store_search(sample_chunks):
    embedder = TFIDFEmbedder()
    vstore = VectorStore(embedder=embedder)
    vstore.add_chunks(sample_chunks)

    results = vstore.search("dilution refrigerator temperature 15 mK", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "15 mK" in top_chunk.content


def test_bm25_index_search(sample_chunks):
    bm25 = BM25Index()
    bm25.add_chunks(sample_chunks)

    results = bm25.search("TX-409 dosage intravenous", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "TX-409" in top_chunk.content


def test_hybrid_retriever_rrf(sample_chunks):
    embedder = TFIDFEmbedder()
    vstore = VectorStore(embedder=embedder)
    vstore.add_chunks(sample_chunks)

    bm25 = BM25Index()
    bm25.add_chunks(sample_chunks)

    retriever = HybridRetriever(vector_store=vstore, bm25_index=bm25, default_alpha=0.5)

    results = retriever.retrieve("What is the monthly uptime percentage SLA?", top_k=2)
    assert len(results) > 0
    top_chunk, fused_score, details = results[0]
    assert "99.95%" in top_chunk.content
    assert "dense_score" in details
    assert "bm25_score" in details
    assert "fused_rrf" in details
