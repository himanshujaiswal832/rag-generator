"""
Grounded Answer Generator orchestrating LLM generation, Guardrails, and Citation Verification
"""

import time
from typing import List, Tuple, Dict, Any, Optional

from rag_generator.core.models import Chunk, GroundedAnswer, Citation
from rag_generator.generation.grounding import GroundingVerifier
from rag_generator.generation.llm_provider import BaseLLMProvider, get_llm_provider


class AnswerGenerator:
    """Coordinates answer synthesis, strict grounding checks, and citation extraction."""

    def __init__(self, default_provider: Optional[BaseLLMProvider] = None):
        self.default_provider = default_provider or get_llm_provider("local_grounded")

    def generate_grounded_answer(
        self,
        question: str,
        retrieved_results: List[Tuple[Chunk, float, Dict[str, Any]]],
        llm_provider: Optional[BaseLLMProvider] = None,
        min_relevance_threshold: float = 0.20,
        temperature: float = 0.1,
        retrieval_latency_ms: float = 0.0,
    ) -> GroundedAnswer:
        """
        Generate a fully grounded answer with citations and anti-hallucination metrics.
        """
        start_gen_time = time.time()
        provider = llm_provider or self.default_provider

        # Check sufficiency of retrieved evidence
        is_sufficient, reason = GroundingVerifier.check_context_sufficiency(
            query=question,
            retrieved_chunks=retrieved_results,
            min_top_score=min_relevance_threshold,
        )

        if not is_sufficient:
            gen_latency_ms = (time.time() - start_gen_time) * 1000.0
            total_latency_ms = retrieval_latency_ms + gen_latency_ms

            # Return explicit refusal rather than hallucination
            chunks_list = [c[0] for c in retrieved_results]
            return GroundedAnswer(
                question=question,
                answer=(
                    f"I cannot find sufficient evidence in the ingested documents to answer your question.\n\n"
                    f"**Reason**: {reason}\n\n"
                    f"*Tip: Try asking about topics covered in the uploaded documents or upload additional reference files.*"
                ),
                citations=[],
                groundedness_score=0.0,
                confidence="Refusal",
                context_coverage=0.0,
                retrieved_chunk_count=len(retrieved_results),
                latency_ms=round(total_latency_ms, 2),
                retrieval_latency_ms=round(retrieval_latency_ms, 2),
                generation_latency_ms=round(gen_latency_ms, 2),
                model_used=provider.provider_name,
                has_sufficient_context=False,
                refusal_reason=reason,
            )

        # Context is sufficient: synthesize answer
        context_chunks = [item[0] for item in retrieved_results]
        raw_answer = provider.generate_answer(
            question=question,
            context_chunks=context_chunks,
            temperature=temperature,
        )

        # Verify grounding and build citations
        groundedness_score, citations = GroundingVerifier.evaluate_groundedness(
            answer_text=raw_answer,
            retrieved_chunks=context_chunks,
        )

        # Attach original hybrid relevance scores to citations
        chunk_score_map = {item[0].chunk_id: item[1] for item in retrieved_results}
        for citation in citations:
            if citation.chunk_id in chunk_score_map:
                citation.relevance_score = round(chunk_score_map[citation.chunk_id], 3)

        # Determine confidence level
        if groundedness_score >= 0.85:
            confidence = "High"
        elif groundedness_score >= 0.50:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Calculate estimated context coverage
        coverage = min(1.0, round(len(retrieved_results) / 4.0, 2))

        gen_latency_ms = (time.time() - start_gen_time) * 1000.0
        total_latency_ms = retrieval_latency_ms + gen_latency_ms

        return GroundedAnswer(
            question=question,
            answer=raw_answer,
            citations=citations,
            groundedness_score=groundedness_score,
            confidence=confidence,
            context_coverage=coverage,
            retrieved_chunk_count=len(retrieved_results),
            latency_ms=round(total_latency_ms, 2),
            retrieval_latency_ms=round(retrieval_latency_ms, 2),
            generation_latency_ms=round(gen_latency_ms, 2),
            model_used=provider.provider_name,
            has_sufficient_context=True,
        )
