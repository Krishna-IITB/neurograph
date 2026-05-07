"""Entity resolution via fuzzy string matching (rapidfuzz).

Same real-world entity often appears with different surface forms:
  "Tesla" / "Tesla Inc" / "Tesla Motors" / "Tesal"

We canonicalize before writing to Neo4j to prevent duplicate nodes.
Talking point: "I used fuzzy matching to unify duplicate entities in the graph."
"""

from .triplet_extractor import Triplet


def canonicalize(entity: str, known: list[str], threshold: int = 90) -> str:
    """Return the canonical form of `entity` if it fuzzy-matches a known one,
    else return `entity` unchanged so it becomes the new canonical."""
    raise NotImplementedError("Phase 1: implement fuzzy canonicalize")


def resolve_triplets(triplets: list[Triplet]) -> list[Triplet]:
    """Apply canonicalize() to head + tail across a batch."""
    raise NotImplementedError("Phase 1: implement batch resolver")
