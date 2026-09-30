"""
Ingestion Pipeline orchestrating Document Loading, Validation, and Chunking
"""

import os
from typing import List, Dict, Any, Union, Tuple
from rag_generator.core.models import Document, Chunk
from rag_generator.ingestion.loaders import DocumentLoader
from rag_generator.ingestion.chunker import RecursiveChunker


class IngestionPipeline:
    """Manages document extraction and chunk generation."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.seen_hashes = set()

    def process_file(self, file_path: str) -> Tuple[Document, List[Chunk]]:
        """Process a single file from disk."""
        doc = DocumentLoader.load_from_file(file_path)
        sha = doc.metadata.get("sha256")
        if sha in self.seen_hashes:
            doc.metadata["is_duplicate"] = True
        else:
            self.seen_hashes.add(sha)
            doc.metadata["is_duplicate"] = False

        chunks = self.chunker.chunk_document(doc)
        return doc, chunks

    def process_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        file_type: str = "text",
    ) -> Tuple[Document, List[Chunk]]:
        """Process in-memory byte buffer (e.g. from HTTP upload)."""
        doc = DocumentLoader.load_from_bytes(file_bytes, filename=filename, file_type=file_type)
        sha = doc.metadata.get("sha256")
        if sha in self.seen_hashes:
            doc.metadata["is_duplicate"] = True
        else:
            self.seen_hashes.add(sha)
            doc.metadata["is_duplicate"] = False

        chunks = self.chunker.chunk_document(doc)
        return doc, chunks

    def process_raw_text(self, text: str, title: str = "Pasted_Note.txt") -> Tuple[Document, List[Chunk]]:
        """Process raw text string."""
        doc = DocumentLoader.load_from_text(text, title=title)
        sha = doc.metadata.get("sha256")
        if sha in self.seen_hashes:
            doc.metadata["is_duplicate"] = True
        else:
            self.seen_hashes.add(sha)
            doc.metadata["is_duplicate"] = False

        chunks = self.chunker.chunk_document(doc)
        return doc, chunks

    def process_directory(self, dir_path: str) -> Tuple[List[Document], List[Chunk]]:
        """Process all supported documents within a directory."""
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        all_docs: List[Document] = []
        all_chunks: List[Chunk] = []

        for root, _, files in os.walk(dir_path):
            for file in files:
                _, ext = os.path.splitext(file.lower())
                if ext in DocumentLoader.SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    try:
                        doc, chunks = self.process_file(file_path)
                        all_docs.append(doc)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")

        return all_docs, all_chunks
