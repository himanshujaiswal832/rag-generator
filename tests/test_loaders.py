"""
Unit Tests for Document Loaders
"""

import pytest
from rag_generator.ingestion.loaders import DocumentLoader


def test_load_from_text():
    text = "This is a sample document for testing text ingestion."
    doc = DocumentLoader.load_from_text(text, title="test_note.txt")

    assert doc.filename == "test_note.txt"
    assert doc.file_type == "text"
    assert doc.content == text
    assert doc.metadata["page_count"] == 1
    assert "sha256" in doc.metadata
    assert doc.char_count == len(text)


def test_load_from_csv_bytes():
    csv_bytes = b"Qubit,Frequency_GHz,T1_us\nQ1,5.2,120\nQ2,5.4,135"
    doc = DocumentLoader.load_from_bytes(csv_bytes, filename="calibration.csv", file_type="csv")

    assert doc.file_type == "csv"
    assert "Table Headers: Qubit, Frequency_GHz, T1_us" in doc.content
    assert "Row 1 -> Qubit: Q1, Frequency_GHz: 5.2, T1_us: 120" in doc.content
    assert "Row 2 -> Qubit: Q2, Frequency_GHz: 5.4, T1_us: 135" in doc.content


def test_load_from_json_bytes():
    json_bytes = b'{"service": "CloudScale", "sla_uptime": 99.95, "regions": ["us-east-1", "us-west-2"]}'
    doc = DocumentLoader.load_from_bytes(json_bytes, filename="policy.json", file_type="json")

    assert doc.file_type == "json"
    assert "CloudScale" in doc.content
    assert "99.95" in doc.content


def test_load_from_html_bytes():
    html_bytes = b"<html><head><title>Research Protocol</title></head><body><h1>Section 1</h1><p>Patient eligibility criteria.</p><script>console.log('strip me');</script></body></html>"
    doc = DocumentLoader.load_from_bytes(html_bytes, filename="protocol.html", file_type="html")

    assert doc.file_type == "html"
    assert "Title: Research Protocol" in doc.content
    assert "Patient eligibility criteria." in doc.content
    assert "console.log" not in doc.content  # script should be stripped
