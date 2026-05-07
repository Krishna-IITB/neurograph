"""Generation-side metrics — LLM-as-judge.

Three metrics, each on a 1-5 scale, returned as floats:

  - Faithfulness: does the answer follow from the retrieved context?
                  (catches hallucinations)
  - Answer Relevance: does the answer address the question asked?
                  (catches off-topic responses)
  - Correctness: does the answer match the expected (gold) answer?
                  (catches factual errors)

Each metric calls the configured LLM with a strict prompt that asks for
ONLY an integer score 1-5. Defensive parsing handles malformed outputs.
"""

from __future__ import annotations

import re

from loguru import logger

from neurograph.generation.llm_client import complete
from neurograph.generation.prompts import (
    ANSWER_RELEVANCE_JUDGE_PROMPT,
    CORRECTNESS_JUDGE_PROMPT,
    FAITHFULNESS_JUDGE_PROMPT,
)


_DIGIT_RE = re.compile(r"[1-5]")


def _parse_score(raw: str) -> float:
    """Pull a 1-5 score out of an LLM response. Returns 0.0 on parse failure."""
    if not raw:
        return 0.0
    # Look for the first 1-5 digit in the response
    match = _DIGIT_RE.search(raw.strip())
    if not match:
        return 0.0
    return float(match.group())


def _judge(prompt: str) -> float:
    """Run a single judge call and return a 1-5 score. 0.0 on error."""
    try:
        raw = complete(prompt, temperature=0.0, max_tokens=10)
    except Exception as e:
        logger.warning(f"Judge call failed: {e}")
        return 0.0
    return _parse_score(raw)


def faithfulness(answer: str, context: str) -> float:
    """Does the answer follow from the context? 1-5, higher = more faithful."""
    if not answer or not context:
        return 0.0
    prompt = FAITHFULNESS_JUDGE_PROMPT.format(answer=answer, context=context)
    return _judge(prompt)


def answer_relevance(answer: str, question: str) -> float:
    """Does the answer address the question? 1-5, higher = more relevant."""
    if not answer or not question:
        return 0.0
    prompt = ANSWER_RELEVANCE_JUDGE_PROMPT.format(answer=answer, question=question)
    return _judge(prompt)


def correctness(generated: str, expected: str) -> float:
    """Does the generated answer match the expected answer? 1-5, higher = more correct."""
    if not generated or not expected:
        return 0.0
    prompt = CORRECTNESS_JUDGE_PROMPT.format(generated=generated, expected=expected)
    return _judge(prompt)
