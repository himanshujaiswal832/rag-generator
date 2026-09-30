"""
Grounding Verification, Source Attribution, and Anti-Hallucination Guardrails
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from rag_generator.core.models import Chunk, Citation


class GroundingVerifier:
    """Verifies that generated answers are strictly grounded in retrieved evidence."""

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "from",
        "of", "is", "are", "was", "were", "be", "been", "that", "this", "these", "those",
        "it", "its", "as", "if", "what", "which", "who", "when", "where", "why", "how",
    }

    @classmethod
    def extract_keywords(cls, text: str) -> List[str]:
        """Extract significant lowercase keywords."""
        words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
        return [w for w in words if w not in cls.STOP_WORDS]

    @classmethod
    def find_best_matching_snippet(
        cls,
        claim: str,
        chunk_content: str,
        max_length: int = 240,
    ) -> str:
        """Find the sentence or clause in chunk_content that most closely matches the claim."""
        sentences = re.split(r"(?<=[.!?])\s+|\n+", chunk_content)
        claim_keywords = set(cls.extract_keywords(claim))

        if not sentences or not claim_keywords:
            return chunk_content[:max_length].strip() + ("..." if len(chunk_content) > max_length else "")

        best_sentence = ""
        best_overlap = -1

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            s_keywords = set(cls.extract_keywords(s_clean))
            overlap = len(claim_keywords.intersection(s_keywords))
            if overlap > best_overlap:
                best_overlap = overlap
                best_sentence = s_clean

        if best_sentence:
            if len(best_sentence) > max_length:
                return best_sentence[:max_length].strip() + "..."
            return best_sentence

        return chunk_content[:max_length].strip() + ("..." if len(chunk_content) > max_length else "")

    @classmethod
    def evaluate_groundedness(
        cls,
        answer_text: str,
        retrieved_chunks: List[Chunk],
    ) -> Tuple[float, List[Citation]]:
        """
        Evaluate sentence-level groundedness of answer_text against retrieved_chunks.
        Returns:
            groundedness_score (0.0 to 1.0)
            citations list
        """
        if not retrieved_chunks or not answer_text.strip():
            return 0.0, []

        # Clean sentences by removing markdown bullets, source tags, and conversational meta-framing
        clean_sentences = []
        for s in re.split(r"(?<=[.!?])\s+|\n+", answer_text):
            s_clean = s.strip()
            # Strip bullet prefixes and markdown
            s_clean = re.sub(r"^[•\-\*\d\.]+\s*", "", s_clean).strip()
            s_clean = re.sub(r"\[Source:[^\]]+\]", "", s_clean, flags=re.IGNORECASE).strip()
            s_clean = re.sub(r"^\*+|\*+$", "", s_clean).strip()
            s_lower = s_clean.lower()
            if not s_clean or len(s_clean) < 8:
                continue
            if s_lower.startswith("based on the provided") or s_lower.startswith("based on **"):
                continue
            if "grounded directly from verified document source" in s_lower:
                continue
            if s_lower.startswith("tip:") or "insufficient evidence" in s_lower:
                continue
            clean_sentences.append(s_clean)

        if not clean_sentences:
            clean_sentences = [answer_text.strip()]

        supported_sentences_count = 0
        citations: List[Citation] = []
        seen_chunks = set()

        # Combine all retrieved text for corpus check
        combined_text = " ".join([c.content for c in retrieved_chunks]).lower()

        for s in clean_sentences:
            s_keywords = cls.extract_keywords(s)
            if not s_keywords:
                supported_sentences_count += 1
                continue

            # Check keyword match against combined retrieved passages
            matched_count = sum(1 for kw in s_keywords if kw in combined_text)
            match_ratio = matched_count / len(s_keywords) if s_keywords else 0.0

            if match_ratio >= 0.35:
                supported_sentences_count += 1

        # Build citations from top retrieved chunks
        for idx, chunk in enumerate(retrieved_chunks):
            if chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk.chunk_id)

            snippet = cls.find_best_matching_snippet(answer_text, chunk.content)
            citations.append(
                Citation(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_name=chunk.source_name,
                    page_number=chunk.page_number,
                    snippet=snippet,
                    relevance_score=round(1.0 - (idx * 0.12), 2),
                    text_match_excerpt=snippet,
                )
            )

        groundedness_score = round(supported_sentences_count / max(1, len(clean_sentences)), 2)
        return groundedness_score, citations

    @classmethod
    def check_context_sufficiency(
        cls,
        query: str,
        retrieved_chunks: List[Tuple[Chunk, float, Any]],
        min_top_score: float = 0.20,
    ) -> Tuple[bool, str]:
        """
        Detect whether retrieved documents actually contain information for the query.
        Returns:
            (is_sufficient, reason_message)
        """
        if not retrieved_chunks:
            return False, "No relevant documents found matching this query."

        top_score = retrieved_chunks[0][1]
        if top_score < min_top_score:
            return False, (
                f"The highest retrieved relevance score ({top_score:.2f}) is below the required "
                f"confidence threshold ({min_top_score:.2f})."
            )

        query_keywords = set(cls.extract_keywords(query))
        combined_content = " ".join([c[0].content for c in retrieved_chunks]).lower()

        overlap = [kw for kw in query_keywords if kw in combined_content]
        overlap_ratio = len(overlap) / max(1, len(query_keywords))

        if overlap_ratio < 0.25 and len(query_keywords) >= 2:
            return False, (
                f"The query concepts ({', '.join(query_keywords)}) have insufficient keyword "
                "presence in the retrieved passages."
            )

        return True, "Sufficient evidence found."
