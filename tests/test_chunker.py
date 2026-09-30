"""
Unit Tests for Recursive Chunker
"""

import pytest
from rag_generator.core.models import Document
from rag_generator.ingestion.chunker import RecursiveChunker


def test_chunker_basic_split():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
    text = (
        "Paragraph one is introducing superconducting qubits and cryogenics.\n\n"
        "Paragraph two discusses surface code thresholds and MWPM decoders.\n\n"
        "Paragraph three covers readout resonators and HEMT amplifiers."
    )
    doc = Document(filename="quantum.txt", file_type="text", content=text)

    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 3
    for c in chunks:
        assert len(c.content) <= 180
        assert c.source_name == "quantum.txt"
        assert c.document_id == doc.document_id
        assert c.token_estimate > 0


def test_chunker_invalid_overlap():
    with pytest.raises(ValueError):
        RecursiveChunker(chunk_size=100, chunk_overlap=120)
