"""Neo4j wrapper for the knowledge graph."""

from .triplet_extractor import Triplet


def upsert_triplets(triplets: list[Triplet]) -> None:
    """Run MERGE queries for all triplets in a single transaction."""
    raise NotImplementedError("Phase 1: implement Neo4j upsert")


def neighbors(entity: str, hops: int | None = None) -> list[dict]:
    """Multi-hop traversal starting at `entity`.

    Returns list of paths as dicts: {"path": ["A", "REL", "B", "REL2", "C"]}.
    """
    raise NotImplementedError("Phase 2: implement multi-hop traversal")
