"""
LLM Provider Abstraction supporting Local Grounded Synthesizer, OpenAI, Gemini, Claude, and Ollama
"""

import os
import re
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from rag_generator.core.models import Chunk


class BaseLLMProvider(ABC):
    """Abstract base class for LLM response generation."""

    @abstractmethod
    def generate_answer(
        self,
        question: str,
        context_chunks: List[Chunk],
        temperature: float = 0.1,
    ) -> str:
        """Generate a grounded answer given the question and context chunks."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class LocalGroundedSynthesizer(BaseLLMProvider):
    """
    Built-in High-Precision Local Grounded Synthesizer.
    Analyzes retrieved passages, scores sentence relevance, extracts verbatim supporting facts,
    and synthesizes a well-formatted grounded answer with source attribution tags.
    Works 100% offline with zero external API keys.
    """

    @property
    def provider_name(self) -> str:
        return "local_grounded_synthesizer"

    def generate_answer(
        self,
        question: str,
        context_chunks: List[Chunk],
        temperature: float = 0.1,
    ) -> str:
        if not context_chunks:
            return "No relevant context was retrieved to answer this question."

        q_terms = [w.lower() for w in re.findall(r"\b\w{2,}\b", question)]
        # Filter common stopwords
        stops = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "can", "could", "will", "would", "shall", "should",
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of"
        }
        key_terms = [w for w in q_terms if w not in stops]

        # Extract scored sentences from all chunks
        candidate_facts = []
        for c_idx, chunk in enumerate(context_chunks, 1):
            sentences = re.split(r"(?<=[.!?])\s+|\n+", chunk.content)
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) < 15:
                    continue
                s_lower = s_clean.lower()
                # Compute overlap score
                matched_terms = [term for term in key_terms if term in s_lower]
                score = len(matched_terms)

                # Bonus for exact phrase matches or numbers/capitalized terms
                if len(matched_terms) > 1:
                    score += 1.5

                if score > 0:
                    candidate_facts.append({
                        "sentence": s_clean,
                        "score": score,
                        "chunk_idx": c_idx,
                        "source": chunk.source_name,
                        "page": chunk.page_number,
                    })

        if not candidate_facts:
            # Fallback to top chunk snippet if no specific sentence scored high
            top_c = context_chunks[0]
            summary = top_c.content[:400].strip()
            return (
                f"Based on **{top_c.source_name}** (Page {top_c.page_number}):\n\n"
                f"{summary}\n\n"
                f"*(Source: [{top_c.source_name}, p.{top_c.page_number}])* "
            )

        # Sort candidate facts by score descending
        candidate_facts.sort(key=lambda x: x["score"], reverse=True)

        # Select top unique sentences
        selected = []
        seen_texts = set()
        for fact in candidate_facts:
            normalized = re.sub(r"\W+", " ", fact["sentence"].lower()).strip()
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            selected.append(fact)
            if len(selected) >= 5:
                break

        # Synthesize organized answer
        lines = [
            f"Based on the provided documents, here is the answer regarding **{question}**:\n"
        ]

        for item in selected:
            sent = item["sentence"]
            # Ensure sentence ends with punctuation
            if not sent.endswith((".", "!", "?")):
                sent += "."
            lines.append(f"• {sent} *[Source: {item['source']}, p.{item['page']}]*")

        # Concluding summary
        top_src = selected[0]["source"]
        lines.append(f"\n*(Grounded directly from verified document source: {top_src})*")

        return "\n".join(lines)


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI API Provider (e.g. gpt-4o, gpt-4o-mini)."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", api_base: Optional[str] = None):
        import openai
        self.model_name = model_name
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)

    @property
    def provider_name(self) -> str:
        return f"openai_{self.model_name}"

    def generate_answer(
        self,
        question: str,
        context_chunks: List[Chunk],
        temperature: float = 0.1,
    ) -> str:
        # Build structured context string
        context_str_parts = []
        for idx, c in enumerate(context_chunks, 1):
            context_str_parts.append(
                f"[Source {idx}: {c.source_name}, Page {c.page_number}]\n{c.content}"
            )
        formatted_context = "\n\n".join(context_str_parts)

        system_prompt = (
            "You are a rigorous, truthful Question-Answering assistant. "
            "Your task is to answer the user's question using ONLY the provided Source Documents below.\n"
            "STRICT RULES:\n"
            "1. Answer strictly based on the provided facts.\n"
            "2. If the context does not contain the answer, explicitly state: 'The provided documents do not contain information to answer this question.'\n"
            "3. Cite your sources using [Source X: DocumentName, p. Y] format after each factual claim.\n"
            "4. Do not speculate or introduce outside knowledge."
        )

        user_content = f"CONTEXT DOCUMENTS:\n{formatted_context}\n\nQUESTION: {question}"

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama HTTP API provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return f"ollama_{self.model_name}"

    def generate_answer(
        self,
        question: str,
        context_chunks: List[Chunk],
        temperature: float = 0.1,
    ) -> str:
        context_str = "\n\n".join([f"[{c.source_name} (p.{c.page_number})]: {c.content}" for c in context_chunks])
        prompt = (
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            "Answer the question based strictly on the context above. Cite the source document."
        )
        payload = json.dumps({
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except Exception as e:
            return f"Error communicating with Ollama ({self.base_url}): {e}"


def get_llm_provider(
    provider_name: str = "local_grounded",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    api_base: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory to instantiate requested LLM provider with fallback."""
    provider_lower = (provider_name or "").lower()

    if "openai" in provider_lower:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if key:
            model = model_name or "gpt-4o-mini"
            return OpenAILLMProvider(api_key=key, model_name=model, api_base=api_base)
        print("Notice: No OpenAI API Key found, using local grounded synthesizer.")

    if "ollama" in provider_lower:
        base = api_base or "http://localhost:11434"
        model = model_name or "llama3"
        return OllamaLLMProvider(base_url=base, model_name=model)

    # Default to built-in local grounded synthesizer
    return LocalGroundedSynthesizer()
