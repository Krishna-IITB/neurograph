"""Build idempotent Cypher MERGE queries from resolved triplets.

Why MERGE and not CREATE: re-running the pipeline must not duplicate nodes.
Generated queries look like:

    MERGE (a:Entity {name: $head})
    MERGE (b:Entity {name: $tail})
    MERGE (a)-[:REL {type: $relation}]->(b)
"""

from .triplet_extractor import Triplet


def build_merge_query(triplet: Triplet) -> tuple[str, dict]:
    """Return (cypher, params) ready for the Neo4j driver."""
    raise NotImplementedError("Phase 1: implement Cypher builder")
