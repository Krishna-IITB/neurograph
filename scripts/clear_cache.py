"""CLI: `python -m scripts.clear_cache`

Wipes the Redis semantic cache. Useful before a live demo so cached
answers from earlier testing don't accidentally serve.

Safe to run anytime — if Redis isn't configured, this is a no-op.
"""

from __future__ import annotations

from neurograph.cache import semantic_cache


def main() -> None:
    if not semantic_cache.is_available():
        print("Cache is not configured (REDIS_URL empty or unreachable). Nothing to clear.")
        return
    n = semantic_cache.clear()
    if n > 0:
        print(f"Cleared {n} cache entries.")
    else:
        print("Cache was already empty.")


if __name__ == "__main__":
    main()
