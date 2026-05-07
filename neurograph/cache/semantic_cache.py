"""Redis-backed semantic cache.

Flow on each query:
  1. Embed the incoming query with the same MiniLM model the index uses.
  2. Scan recent cache entries in Redis, compute cosine similarity to each.
  3. If the best match scores ≥ settings.cache_threshold (default 0.95),
     return the cached answer. Otherwise miss.
  4. On miss, the caller runs the full pipeline and `store()`s the result.

Why threshold 0.95: empirically calibrated.
  - 0.80 → false positives ("CEO of Tesla" hits "founder of Tesla")
  - 0.99 → almost no cache hits
  - 0.95 → the production sweet spot

Storage shape:
  Key:    `ngcache:entry:<hex8>`
  Value:  JSON {"query": str, "answer": str, "embedding": [384 floats], "ts": float}
  Index:  `ngcache:keys` — a SET of all entry keys (for O(N) scans without KEYS)

The cache degrades gracefully: if Redis is unreachable or REDIS_URL is
unset, all calls become silent no-ops. The system still works without
caching, just slower.
"""

from __future__ import annotations

import hashlib
import json
import time
from functools import lru_cache

import numpy as np
from loguru import logger

from neurograph.config import settings

_KEY_PREFIX = "ngcache:entry:"
_INDEX_KEY = "ngcache:keys"
_MAX_ENTRIES = 1000  # bounded to keep scan cheap and stay inside Upstash free tier


@lru_cache(maxsize=1)
def _client():
    """Return a lazily-initialized Redis client, or None if unavailable."""
    if not settings.redis_url:
        return None
    try:
        import redis

        c = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3.0)
        c.ping()
        logger.info("Semantic cache: Redis connected")
        return c
    except Exception as e:
        logger.warning(f"Semantic cache: Redis unavailable ({type(e).__name__}: {e}) — cache disabled")
        return None


def is_available() -> bool:
    """True if Redis is configured AND reachable."""
    return _client() is not None


def _embed(query: str) -> np.ndarray:
    """Embed a query using the same model as the vector index."""
    # Reach into the singleton to reuse the loaded model — avoids second 80MB load
    from neurograph.indexing.vector_store import _store

    embedder = _store()._embedder
    return np.array(embedder.encode([query])[0])


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _key_for(query: str) -> str:
    """Stable per-query cache key. Hash so weird chars don't break Redis keys."""
    h = hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]
    return f"{_KEY_PREFIX}{h}"


def lookup(query: str) -> tuple[str, float] | None:
    """Return (answer, score) if a sufficiently similar query exists in cache.

    Returns None on cache miss, when Redis is unavailable, or on any error.
    """
    c = _client()
    if not c:
        return None

    try:
        keys = list(c.smembers(_INDEX_KEY))
    except Exception as e:
        logger.warning(f"Cache lookup failed (smembers): {e}")
        return None
    if not keys:
        return None

    try:
        q_emb = _embed(query)
    except Exception as e:
        logger.warning(f"Cache lookup failed (embed): {e}")
        return None

    best_score = 0.0
    best_answer: str | None = None

    try:
        # Pipeline the gets to amortize round-trip latency
        pipe = c.pipeline()
        for k in keys:
            pipe.get(k)
        values = pipe.execute()
    except Exception as e:
        logger.warning(f"Cache lookup failed (mget): {e}")
        return None

    stale: list[str] = []
    for k, raw in zip(keys, values):
        if not raw:
            stale.append(k)
            continue
        try:
            entry = json.loads(raw)
            score = _cosine(q_emb, np.array(entry["embedding"]))
        except Exception:
            stale.append(k)
            continue
        if score >= settings.cache_threshold and score > best_score:
            best_score = score
            best_answer = entry.get("answer")

    # Cleanup index entries whose values disappeared (TTL expired or evicted)
    if stale:
        try:
            c.srem(_INDEX_KEY, *stale)
        except Exception:
            pass

    if best_answer is None:
        return None
    return best_answer, best_score


def store(query: str, answer: str, ttl_seconds: int = 7 * 24 * 3600) -> None:
    """Persist a (query, answer) pair for future hits. Silent on failure."""
    c = _client()
    if not c or not query or not answer:
        return
    try:
        emb = _embed(query).tolist()
    except Exception as e:
        logger.warning(f"Cache store failed (embed): {e}")
        return

    key = _key_for(query)
    payload = json.dumps(
        {"query": query, "answer": answer, "embedding": emb, "ts": time.time()}
    )
    try:
        pipe = c.pipeline()
        pipe.set(key, payload, ex=ttl_seconds)
        pipe.sadd(_INDEX_KEY, key)
        pipe.execute()
    except Exception as e:
        logger.warning(f"Cache store failed: {e}")
        return

    # Bound the index — drop the oldest if we cross the limit
    try:
        size = c.scard(_INDEX_KEY)
        if size > _MAX_ENTRIES:
            # Coarse eviction: just remove a random member from the index.
            # The orphaned entry will TTL out.
            victim = c.spop(_INDEX_KEY)
            if victim:
                logger.debug(f"Cache evicted: {victim}")
    except Exception:
        pass


def clear() -> int:
    """Wipe the cache. Returns count of entries removed. Dev/testing only."""
    c = _client()
    if not c:
        return 0
    try:
        keys = list(c.smembers(_INDEX_KEY))
        if not keys:
            return 0
        c.delete(*keys, _INDEX_KEY)
        return len(keys)
    except Exception as e:
        logger.warning(f"Cache clear failed: {e}")
        return 0


def stats() -> dict:
    """Return cache size and threshold for observability."""
    c = _client()
    return {
        "available": c is not None,
        "size": c.scard(_INDEX_KEY) if c else 0,
        "threshold": settings.cache_threshold,
    }
