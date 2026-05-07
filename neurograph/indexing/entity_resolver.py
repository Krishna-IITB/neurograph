"""Entity resolution via fuzzy string matching (rapidfuzz / Levenshtein).

The same real-world entity often shows up with surface variations:
    "Tesla" / "Tesla Inc" / "Tesla Motors" / "Tesal"
    "SpaceX" / "Space X" / "Space-X"

We canonicalize before writing to Neo4j to prevent duplicate nodes.

Talking point: "I used fuzzy matching with Levenshtein distance to unify
duplicate entities in the graph."
"""

from __future__ import annotations

from loguru import logger
from rapidfuzz import fuzz, process

from neurograph.indexing.triplet_extractor import Triplet

DEFAULT_THRESHOLD = 90  # 0..100. 90 = "Tesla" matches "Tesla Inc" but not "Tesco"


def canonicalize(
    entity: str,
    known: list[str],
    threshold: int = DEFAULT_THRESHOLD,
) -> str:
    """Return the canonical form of `entity` if it fuzzy-matches a known one,
    else return `entity` unchanged so it becomes the new canonical."""
    if not entity:
        return entity
    if not known:
        return entity
    # token_set_ratio handles word reorderings and partial overlaps better
    # than plain ratio — "Tesla Inc" vs "Inc, Tesla" both score high.
    match = process.extractOne(entity, known, scorer=fuzz.token_set_ratio)
    if match and match[1] >= threshold:
        return match[0]
    return entity


def resolve_triplets(
    triplets: list[Triplet],
    threshold: int = DEFAULT_THRESHOLD,
) -> list[Triplet]:
    """Apply canonicalize() to head + tail across a batch.

    Maintains a running list of canonical entities; the first surface form
    seen wins (consider this in the future — could canonicalize to longest
    or most-frequent form instead).
    """
    known: list[str] = []
    out: list[Triplet] = []
    for t in triplets:
        head = canonicalize(t.head, known, threshold)
        if head not in known:
            known.append(head)
        tail = canonicalize(t.tail, known, threshold)
        if tail not in known:
            known.append(tail)
        out.append(
            Triplet(
                head=head,
                relation=t.relation,
                tail=tail,
                source_chunk_id=t.source_chunk_id,
            )
        )
    logger.info(
        f"Resolved {len(triplets)} triplets → {len(known)} canonical entities "
        f"(threshold={threshold})"
    )
    return out
