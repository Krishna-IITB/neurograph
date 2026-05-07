"""Graph retrieval — extract entities from the query, walk the graph.

Pipeline:
  1. Extract entities from query via LLM (or simple NER fallback).
  2. For each entity, fetch N-hop neighborhood from Neo4j.
  3. Format paths as natural-language triples for prompt injection.
"""


def retrieve(query: str, hops: int | None = None) -> list[str]:
    """Return list of human-readable path strings, e.g.:
        "Elon Musk --FOUNDED--> SpaceX --TARGETS--> Mars"
    """
    raise NotImplementedError("Phase 2: graph retrieval")
