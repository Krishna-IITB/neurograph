"""Unit tests for the semantic cache.

Uses monkeypatch to swap out the Redis client and embedding function so
tests run without any external services.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from neurograph.cache import semantic_cache


class FakeRedisPipeline:
    """In-memory pipeline that just batches commands until execute()."""

    def __init__(self, store: "FakeRedis"):
        self.store = store
        self.queue: list = []

    def get(self, key):
        self.queue.append(("get", key))
        return self

    def set(self, key, value, ex=None):
        self.queue.append(("set", key, value, ex))
        return self

    def sadd(self, key, *members):
        self.queue.append(("sadd", key, members))
        return self

    def execute(self):
        results = []
        for cmd in self.queue:
            if cmd[0] == "get":
                results.append(self.store.get(cmd[1]))
            elif cmd[0] == "set":
                self.store.set(cmd[1], cmd[2], ex=cmd[3])
                results.append(True)
            elif cmd[0] == "sadd":
                for m in cmd[2]:
                    self.store._sets.setdefault(cmd[1], set()).add(m)
                results.append(len(cmd[2]))
        self.queue.clear()
        return results


class FakeRedis:
    def __init__(self):
        self._kv: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}

    def ping(self):
        return True

    def get(self, key):
        return self._kv.get(key)

    def set(self, key, value, ex=None):
        self._kv[key] = value

    def smembers(self, key):
        return self._sets.get(key, set())

    def sadd(self, key, *members):
        self._sets.setdefault(key, set()).update(members)
        return len(members)

    def srem(self, key, *members):
        s = self._sets.get(key, set())
        for m in members:
            s.discard(m)
        return len(members)

    def scard(self, key):
        return len(self._sets.get(key, set()))

    def spop(self, key):
        s = self._sets.get(key, set())
        return s.pop() if s else None

    def delete(self, *keys):
        for k in keys:
            self._kv.pop(k, None)
            self._sets.pop(k, None)
        return len(keys)

    def pipeline(self):
        return FakeRedisPipeline(self)


@pytest.fixture
def fake_cache(monkeypatch):
    """Wire up the cache module to use a FakeRedis and deterministic embeddings."""
    fake = FakeRedis()
    semantic_cache._client.cache_clear()
    monkeypatch.setattr(semantic_cache, "_client", lambda: fake)

    # Deterministic, simple embedding: hash the query to a fixed-length vector.
    # This lets us control similarity in tests.
    def fake_embed(query: str) -> np.ndarray:
        # Trivial: each unique query → unique vector; queries with same prefix
        # will overlap meaningfully via dot product.
        rng = np.random.default_rng(abs(hash(query)) % (2**31))
        return rng.standard_normal(8)

    monkeypatch.setattr(semantic_cache, "_embed", fake_embed)
    return fake


def test_no_redis_returns_none(monkeypatch):
    """When _client returns None, lookup is a no-op returning None."""
    semantic_cache._client.cache_clear()
    monkeypatch.setattr(semantic_cache, "_client", lambda: None)
    assert semantic_cache.lookup("anything") is None
    semantic_cache.store("anything", "some answer")  # should not raise
    assert semantic_cache.is_available() is False


def test_lookup_empty_cache(fake_cache):
    assert semantic_cache.lookup("test") is None


def test_store_then_lookup_exact_match(fake_cache):
    semantic_cache.store("Who founded Tesla?", "Martin Eberhard and Marc Tarpenning")
    hit = semantic_cache.lookup("Who founded Tesla?")
    assert hit is not None
    answer, score = hit
    assert answer == "Martin Eberhard and Marc Tarpenning"
    assert score >= 0.99  # exact match → cosine ~1.0


def test_lookup_below_threshold_misses(fake_cache, monkeypatch):
    """Different queries → different deterministic vectors → low cosine → miss."""
    monkeypatch.setattr("neurograph.config.settings.cache_threshold", 0.95)
    semantic_cache.store("Who founded Tesla?", "Eberhard and Tarpenning")
    # Different query gets a different random vector, very unlikely to score ≥ 0.95
    assert semantic_cache.lookup("What is the capital of France?") is None


def test_clear_wipes_cache(fake_cache):
    semantic_cache.store("q1", "a1")
    semantic_cache.store("q2", "a2")
    assert semantic_cache.stats()["size"] == 2
    removed = semantic_cache.clear()
    assert removed == 2
    assert semantic_cache.stats()["size"] == 0


def test_stats_reports_availability(fake_cache):
    semantic_cache.store("q1", "a1")
    s = semantic_cache.stats()
    assert s["available"] is True
    assert s["size"] == 1
    assert 0.0 < s["threshold"] <= 1.0


def test_store_skips_empty_inputs(fake_cache):
    semantic_cache.store("", "answer")
    semantic_cache.store("query", "")
    assert semantic_cache.stats()["size"] == 0


def test_corrupted_entry_is_cleaned_up(fake_cache):
    """If an entry's JSON value is corrupt, it should be removed from the index."""
    fake_cache._kv["ngcache:entry:bad"] = "not valid json {"
    fake_cache._sets["ngcache:keys"] = {"ngcache:entry:bad"}
    assert semantic_cache.lookup("anything") is None
    # The corrupted entry should now be removed from the index set
    assert "ngcache:entry:bad" not in fake_cache._sets.get("ngcache:keys", set())
