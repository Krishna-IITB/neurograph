"""Build idempotent Cypher MERGE queries from resolved triplets.

Why MERGE (and not CREATE): re-running the pipeline must not duplicate
nodes. MERGE is "create if missing, reuse if exists" — making the whole
ingestion pipeline idempotent.

Talking point: "I translated extracted triplets into Cypher MERGE queries
to ensure idempotent graph construction."
"""

from __future__ import annotations

import re

from neurograph.indexing.triplet_extractor import Triplet


def _safe_rel_type(rel: str) -> str:
    """Cypher relationship types must be valid identifiers.
    Falls back to RELATED_TO if normalization leaves an empty string.
    """
    rel = rel.strip().upper()
    rel = re.sub(r"\s+", "_", rel)
    rel = re.sub(r"[^A-Z0-9_]", "", rel)
    rel = re.sub(r"_+", "_", rel).strip("_")
    # Cypher identifiers can't start with a digit
    if not rel or rel[0].isdigit():
        rel = f"REL_{rel}" if rel else "RELATED_TO"
    return rel


def build_merge_query(triplet: Triplet) -> tuple[str, dict]:
    """Build (cypher, params) for a single triplet.

    Returns a query that:
      - MERGEs the head Entity node by name
      - MERGEs the tail Entity node by name
      - MERGEs a typed relationship between them
      - records source_chunk_id on the relationship for provenance
    """
    rel_type = _safe_rel_type(triplet.relation)

    cypher = (
        f"MERGE (h:Entity {{name: $head}}) "
        f"MERGE (t:Entity {{name: $tail}}) "
        f"MERGE (h)-[r:{rel_type}]->(t) "
        f"SET r.source_chunk_id = coalesce($source_chunk_id, r.source_chunk_id)"
    )
    params = {
        "head": triplet.head,
        "tail": triplet.tail,
        "source_chunk_id": triplet.source_chunk_id,
    }
    return cypher, params
