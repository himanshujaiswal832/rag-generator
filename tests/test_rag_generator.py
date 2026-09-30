"""
End-to-End Tests for RAG Factory: Multi-App Creation, Ingestion, and Isolation
"""

import os
import shutil
import tempfile
import pytest

from rag_generator.core.factory import RAGFactory
from rag_generator.core.models import QueryRequest, RAGAppConfig


@pytest.fixture
def temp_factory():
    tmp_dir = tempfile.mkdtemp()
    factory = RAGFactory(storage_root=tmp_dir)
    yield factory
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_create_and_query_rag_app(temp_factory):
    # App 1: Medical Study
    med_text = (
        "TX-409 Protocol: Standard dosage is 8.0 mg/kg intravenous infusion every 3 weeks. "
        "Primary endpoints are Objective Response Rate (ORR) and Progression-Free Survival (PFS)."
    )
    app1 = temp_factory.create_app(
        name="Oncology App",
        description="Medical trials",
        raw_texts=[{"title": "tx409.txt", "content": med_text}],
    )

    assert app1.app_id.startswith("oncology-app")
    meta1 = app1.get_metadata()
    assert meta1.document_count == 1
    assert meta1.chunk_count >= 1

    # Query App 1
    res1 = app1.query(QueryRequest(question="What is the standard dosage for TX-409?"))
    assert res1.has_sufficient_context
    assert "8.0 mg/kg" in res1.answer
    assert len(res1.citations) >= 1
    assert res1.groundedness_score > 0.5


def test_multi_domain_isolation(temp_factory):
    # Create Quantum App
    app_q = temp_factory.create_app(
        name="Quantum App",
        raw_texts=[{"title": "quantum.txt", "content": "The dilution refrigerator base temperature is 15 mK."}],
    )

    # Create Legal App
    app_l = temp_factory.create_app(
        name="Legal App",
        raw_texts=[{"title": "legal.txt", "content": "The aggregate liability cap is strictly $5,000,000 USD."}],
    )

    # Query Quantum app for legal question -> should refuse
    res_cross = app_q.query(QueryRequest(question="What is the liability cap under Section 11?"))
    assert not res_cross.has_sufficient_context
    assert res_cross.confidence == "Refusal"

    # Query Legal app for legal question -> should succeed
    res_legal = app_l.query(QueryRequest(question="What is the liability cap?"))
    assert res_legal.has_sufficient_context
    assert "$5,000,000" in res_legal.answer


def test_runtime_document_addition(temp_factory):
    app = temp_factory.create_app(
        name="Dynamic App",
        raw_texts=[{"title": "doc1.txt", "content": "Initial policy on remote work allows 2 days per week."}],
    )
    assert app.get_metadata().document_count == 1

    # Ingest another document at runtime
    app.ingest_raw_text(
        text="Updated equipment budget policy allocates $1,500 per remote employee annually.",
        title="budget_policy.txt",
    )

    meta = app.get_metadata()
    assert meta.document_count == 2
    assert meta.chunk_count >= 2

    # Query new document
    res = app.query(QueryRequest(question="What is the equipment budget allocation?"))
    assert res.has_sufficient_context
    assert "$1,500" in res.answer
