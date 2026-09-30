"""
Unit Tests for Grounding Verification and Anti-Hallucination Guardrails
"""

import pytest
from rag_generator.core.models import Chunk
from rag_generator.generation.grounding import GroundingVerifier


def test_find_best_matching_snippet():
    content = (
        "The processor operates at base temperature. "
        "The aggregate liability cap is strictly limited to $5,000,000 USD under Section 11. "
        "All invoices are payable Net-30."
    )
    claim = "Liability is capped at $5,000,000 under Section 11."
    snippet = GroundingVerifier.find_best_matching_snippet(claim, content)

    assert "$5,000,000" in snippet
    assert "Section 11" in snippet


def test_evaluate_groundedness():
    chunk = Chunk(
        document_id="d1",
        source_name="contract.md",
        content="The aggregate liability cap is strictly limited to $5,000,000 USD or fees paid in 12 months.",
        chunk_index=0,
    )
    answer = "Under the agreement, total liability is capped at $5,000,000 USD."

    score, citations = GroundingVerifier.evaluate_groundedness(answer, [chunk])

    assert score >= 0.8
    assert len(citations) == 1
    assert citations[0].source_name == "contract.md"
    assert "$5,000,000" in citations[0].snippet


def test_context_sufficiency_refusal():
    # Irrelevant query
    chunk = Chunk(
        document_id="d1",
        source_name="qubits.txt",
        content="Superconducting transmons operate at microwave frequencies between 4 and 8 GHz.",
        chunk_index=0,
    )
    retrieved = [(chunk, 0.05, {})]

    is_sufficient, reason = GroundingVerifier.check_context_sufficiency(
        query="What is the capital of France and who is the prime minister?",
        retrieved_chunks=retrieved,
        min_top_score=0.20,
    )

    assert not is_sufficient
    assert "below the required confidence threshold" in reason
