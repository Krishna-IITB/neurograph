"""LLM-based triplet extraction.

Asks the LLM to extract (head, relation, tail) from a chunk.
Output is structured JSON so downstream code can build Cypher cleanly.

Example input:  "Elon Musk is the CEO of Tesla."
Example output: {"head": "Elon Musk", "relation": "CEO_OF", "tail": "Tesla"}
"""

from pydantic import BaseModel


class Triplet(BaseModel):
    head: str
    relation: str
    tail: str
    source_chunk_id: str | None = None


def extract_triplets(text: str, *, source_chunk_id: str | None = None) -> list[Triplet]:
    """Run a single LLM extraction pass. Returns 0..N triplets."""
    raise NotImplementedError("Phase 1: implement triplet extractor")
