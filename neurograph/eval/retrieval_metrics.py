"""Retrieval-side metrics.

We use a **token-level recall** proxy rather than chunk-id Hit Rate / MRR
because the gold dataset doesn't pin specific chunk_ids.

The metric: tokenize the expected answer into content words (dropping
stopwords + 1-char tokens), then count what fraction appear as substrings
in the retrieved text. If ≥ threshold (default 0.5), it's a hit.

Why this beats fuzz.partial_ratio: substring fuzzy matching of full
sentences fails when the answer's information is spread across the chunk.
Token-level handles paraphrasing, word reordering, and partial overlap
correctly. This is the same approach RAGAS uses for context_recall.

For interview pitch, call this "Token Recall@k" or "Answer-token coverage".
"""

from __future__ import annotations

import re

from langchain_core.documents import Document

DEFAULT_THRESHOLD = 0.5

# Common English function words — ignored when computing recall so that
# distinctive content words drive the metric.
_STOPWORDS = frozenset({
    "the", "a", "an", "is", "was", "were", "be", "been", "being", "are", "am",
    "of", "in", "on", "at", "by", "for", "to", "from", "with", "into", "onto",
    "and", "or", "but", "as", "if", "that", "this", "these", "those", "it",
    "its", "his", "her", "their", "they", "them", "had", "have", "has", "do",
    "does", "did", "not", "no", "so", "than", "then", "such", "also", "which",
    "who", "whom", "whose", "where", "when", "why", "how", "what",
})

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _content_tokens(text: str) -> list[str]:
    """Lowercase, split on word chars, drop stopwords and 1-char tokens."""
    return [
        t for t in _TOKEN_RE.findall(text.lower())
        if t not in _STOPWORDS and len(t) > 1
    ]


def keyword_recall(
    retrieved_text: str,
    expected_answer: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> float:
    """Return 1.0 if at least `threshold` fraction of expected content tokens
    appear in the retrieved text, else 0.0.

    Example:
        retrieved = "Tesla was founded by Eberhard and Tarpenning in July 2003."
        expected  = "Tesla was founded in July 2003."
        content tokens of expected = ["tesla", "founded", "july", "2003"]
        all 4 appear in retrieved → recall = 1.0
    """
    if not retrieved_text or not expected_answer:
        return 0.0
    expected_tokens = _content_tokens(expected_answer)
    if not expected_tokens:
        return 0.0
    retrieved_lower = retrieved_text.lower()
    hits = sum(1 for t in expected_tokens if t in retrieved_lower)
    fraction = hits / len(expected_tokens)
    return 1.0 if fraction >= threshold else 0.0


def keyword_recall_for_chunks(
    chunks: list[Document],
    expected_answer: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> float:
    """Concatenate chunk text and check token-level recall."""
    if not chunks:
        return 0.0
    concat = "\n".join(d.page_content for d in chunks)
    return keyword_recall(concat, expected_answer, threshold)


def keyword_recall_for_paths(
    paths: list[str],
    expected_answer: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> float:
    """Concatenate graph paths and check token-level recall.

    Note: graph paths use UPPERCASE_SNAKE_CASE for relations
    (e.g., "Elon Musk --FOUNDED--> SpaceX"). The token splitter handles this
    naturally — it'll extract "founded" as a token.
    """
    if not paths:
        return 0.0
    concat = "\n".join(paths)
    return keyword_recall(concat, expected_answer, threshold)


def average(scores: list[float]) -> float:
    """Mean of a list of metric scores. 0.0 if empty."""
    return sum(scores) / len(scores) if scores else 0.0
