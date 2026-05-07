"""End-to-end Q&A engine.

Pipeline:
  1. Check semantic cache (skipped if Redis unavailable).
  2. On miss, run hybrid retrieval + LLM generation.
  3. On success, write the answer back to the cache for future hits.

The cache layer is opt-in (controlled per call by `use_cache=True`).
Falls back gracefully when no Redis is configured.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from neurograph.cache import semantic_cache
from neurograph.generation.llm_client import complete
from neurograph.generation.prompts import ANSWER_PROMPT
from neurograph.retrieval.hybrid import Mode, RetrievalResult, format_context, retrieve


@dataclass
class QAResponse:
    answer: str
    retrieval: RetrievalResult
    mode: Mode
    latency_ms: float
    cache_hit: bool = False
    cache_score: float | None = None


def answer(
    question: str,
    *,
    mode: Mode = "hybrid",
    k: int | None = None,
    hops: int | None = None,
    temperature: float = 0.0,
    max_tokens: int = 700,
    use_cache: bool = True,
) -> QAResponse:
    """Run retrieval + generation and return a structured response.

    Args:
        question: User's natural language question.
        mode: 'vector' | 'graph' | 'hybrid'.
        k: Vector top-k override.
        hops: Graph traversal hops override.
        temperature: LLM sampling temperature.
        max_tokens: Generation cap.
        use_cache: Check (and write to) the semantic cache. Default True.
    """
    t0 = time.perf_counter()

    # Step 1: cache lookup -------------------------------------------------
    if use_cache:
        hit = semantic_cache.lookup(question)
        if hit is not None:
            cached_answer, score = hit
            logger.info(f"cache HIT (cosine={score:.3f}) for: '{question[:60]}'")
            return QAResponse(
                answer=cached_answer,
                retrieval=RetrievalResult(chunks=[], paths=[], mode=mode),
                mode=mode,
                latency_ms=(time.perf_counter() - t0) * 1000,
                cache_hit=True,
                cache_score=score,
            )

    # Step 2: retrieval ----------------------------------------------------
    rr = retrieve(question, mode=mode, k=k, hops=hops)
    if not rr.has_content():
        return QAResponse(
            answer="I don't have enough information in the indexed documents to answer that question.",
            retrieval=rr,
            mode=mode,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # Step 3: generation ---------------------------------------------------
    context = format_context(rr.chunks, rr.paths)
    prompt = ANSWER_PROMPT.format(context=context, question=question)

    try:
        text = complete(prompt, temperature=temperature, max_tokens=max_tokens)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return QAResponse(
            answer=f"(generation error: {e})",
            retrieval=rr,
            mode=mode,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    final_answer = text.strip()

    # Step 4: cache write --------------------------------------------------
    if use_cache and final_answer and not final_answer.startswith("(generation error"):
        semantic_cache.store(question, final_answer)

    return QAResponse(
        answer=final_answer,
        retrieval=rr,
        mode=mode,
        latency_ms=(time.perf_counter() - t0) * 1000,
    )
