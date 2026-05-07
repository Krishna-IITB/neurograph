"""Redis-backed semantic cache.

Flow:
  1. Embed the incoming query.
  2. Search Redis for the closest stored query embedding.
  3. If cosine ≥ settings.cache_threshold (default 0.95), return the cached answer.
  4. Otherwise, run the full pipeline and write the result back.

Threshold of 0.95 was empirically calibrated:
  - 0.80 → false positives ("CEO of Tesla" hitting "founder of Tesla")
  - 0.99 → cache rarely used
  - 0.95 → balanced sweet spot
"""


def lookup(query: str) -> str | None:
    """Return cached answer if a match exists above threshold, else None."""
    raise NotImplementedError("Phase 3: implement cache lookup")


def store(query: str, answer: str) -> None:
    """Persist (query embedding, answer) for future hits."""
    raise NotImplementedError("Phase 3: implement cache write")
