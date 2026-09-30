"""
Recursive Semantic Chunker with Boundary Detection and Page Tracking
"""

import re
from typing import List, Optional
from rag_generator.core.models import Document, Chunk


class RecursiveChunker:
    """Intelligently splits text into semantic chunks respecting structural boundaries."""

    SEPARATORS = [
        "\n\n\n",
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        "; ",
        ", ",
        " ",
        "",
    ]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Split an ingested document into a list of Chunk objects."""
        chunks: List[Chunk] = []
        chunk_idx = 0

        # If document has distinct page information (e.g. multi-page PDF)
        if document.pages and len(document.pages) > 1:
            for page_info in document.pages:
                page_num = page_info.get("page_number", 1)
                page_text = page_info.get("text", "")
                if not page_text.strip():
                    continue

                page_chunks = self._split_text(page_text)
                for c_text in page_chunks:
                    c_text = c_text.strip()
                    if not c_text:
                        continue
                    chunks.append(
                        Chunk(
                            document_id=document.document_id,
                            source_name=document.filename,
                            content=c_text,
                            chunk_index=chunk_idx,
                            page_number=page_num,
                            token_estimate=max(1, len(c_text) // 4),
                            metadata={
                                "file_type": document.file_type,
                                "page_number": page_num,
                                "original_filename": document.filename,
                            },
                        )
                    )
                    chunk_idx += 1
            return chunks

        # Otherwise chunk the entire document content
        raw_chunks = self._split_text(document.content)
        current_offset = 0

        for c_text in raw_chunks:
            c_text = c_text.strip()
            if not c_text:
                continue

            start_char = document.content.find(c_text, current_offset)
            if start_char == -1:
                start_char = current_offset
            end_char = start_char + len(c_text)
            current_offset = max(start_char + 1, current_offset)

            # Heuristic to detect page markers like "--- Page X ---"
            page_match = re.search(r"--- Page (\d+) ---", c_text)
            page_num = int(page_match.group(1)) if page_match else 1

            chunks.append(
                Chunk(
                    document_id=document.document_id,
                    source_name=document.filename,
                    content=c_text,
                    chunk_index=chunk_idx,
                    page_number=page_num,
                    start_char=start_char,
                    end_char=end_char,
                    token_estimate=max(1, len(c_text) // 4),
                    metadata={
                        "file_type": document.file_type,
                        "page_number": page_num,
                        "original_filename": document.filename,
                    },
                )
            )
            chunk_idx += 1

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Recursively split text using hierarchy of separators."""
        return self._recursive_split(text, self.SEPARATORS)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            # Character-level fallback split
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        splits = text.split(separator)
        good_splits: List[str] = []

        for s in splits:
            if not s.strip():
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                other_chunks = self._recursive_split(s, remaining_separators)
                final_chunks.extend(other_chunks)

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Combine smaller pieces with sliding window overlap up to chunk_size."""
        docs: List[str] = []
        current_doc: List[str] = []
        total = 0

        for d in splits:
            _len = len(d) + (len(separator) if current_doc else 0)
            if total + _len > self.chunk_size:
                if total > 0:
                    joined = separator.join(current_doc)
                    if joined.strip():
                        docs.append(joined.strip())
                    # Keep overlap from the end
                    while total > self.chunk_overlap and len(current_doc) > 1:
                        removed = current_doc.pop(0)
                        total -= len(removed) + len(separator)
                else:
                    current_doc = []
                    total = 0

            current_doc.append(d)
            total += _len

        if current_doc:
            joined = separator.join(current_doc)
            if joined.strip():
                docs.append(joined.strip())

        return docs
