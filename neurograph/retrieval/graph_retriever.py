"""Graph retrieval — extract entities from the query, walk the graph.

Pipeline:
  1. Extract entities from query via LLM (strict JSON list).
  2. For each entity, fuzzy-match to a known graph entity if not exact.
  3. For each matched entity, fetch N-hop neighborhood from Neo4j.
  4. Format paths as natural-language triples for prompt injection.

Talking point: "graph retrieval lets the system answer multi-hop questions
like 'Which companies did the founder of SpaceX also start?' that vector
search alone cannot."
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from loguru import logger
from rapidfuzz import fuzz, process

from neurograph.config import settings
from neurograph.generation.llm_client import complete, is_available
from neurograph.generation.prompts import ENTITY_EXTRACT_PROMPT
from neurograph.indexing import graph_store

_FENCE_RE = re.compile(r"```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json_list(text: str) -> list[str]:
    """Defensive: pull a JSON list of strings out of the LLM response."""
    if not text:
        return []
    cleaned = _FENCE_RE.sub("", text.strip())
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [str(x).strip() for x in data if isinstance(x, (str, int, float)) and str(x).strip()]


def extract_entities_from_query(question: str) -> list[str]:
    """LLM-based entity extraction from the user question."""
    if not is_available():
        logger.warning("Graph retrieval: no LLM provider — returning [] entities")
        return []
    prompt = ENTITY_EXTRACT_PROMPT.format(question=question)
    try:
        raw = complete(prompt, temperature=0.0, max_tokens=200)
    except Exception as e:
        logger.warning(f"Graph retrieval entity extraction failed: {e}")
        return []
    return _extract_json_list(raw)


@lru_cache(maxsize=1)
def _all_entity_names() -> list[str]:
    """Cache the list of canonical entity names from Neo4j (one Cypher call).

    We use this for fuzzy-matching query entities to graph entities — the
    LLM might output 'Musk' when the graph has 'Elon Musk'.
    """
    if not graph_store.is_configured():
        return []
    try:
        # Reach into the singleton driver for a quick lookup
        store = graph_store._store()
        with store._driver.session() as s:
            result = s.run("MATCH (n:Entity) RETURN n.name AS name")
            return [r["name"] for r in result if r["name"]]
    except Exception as e:
        logger.warning(f"Could not load entity names for fuzzy match: {e}")
        return []


def _resolve_to_graph_entity(name: str, threshold: int = 80) -> str | None:
    """Find the closest matching entity name in the graph.

    Returns None if no good match — that entity isn't in the graph at all.
    """
    known = _all_entity_names()
    if not known or not name:
        return None
    if name in known:
        return name
    match = process.extractOne(name, known, scorer=fuzz.token_set_ratio)
    if match and match[1] >= threshold:
        return match[0]
    return None


def _format_path(segments: list[dict]) -> str:
    """Convert structured segments into a human-readable path string.

    Input shape (from graph_store.neighbors):
        [{"type": "node", "name": "Elon Musk"},
         {"type": "rel",  "name": "FOUNDED", "dir": "out"},
         {"type": "node", "name": "SpaceX"}]

    Output: "Elon Musk --FOUNDED--> SpaceX"
    Inbound rel: "Tesla <--IS_LEADER_OF-- Elon Musk"
    """
    parts: list[str] = []
    for seg in segments:
        if seg.get("type") == "node":
            parts.append(seg["name"])
        elif seg.get("type") == "rel":
            arrow = f"--{seg['name']}-->" if seg.get("dir") == "out" else f"<--{seg['name']}--"
            parts.append(arrow)
        else:
            # Backward-compat: tolerate plain strings if any caller still passes them
            parts.append(str(seg))
    return " ".join(parts)


def retrieve(query: str, hops: int | None = None, max_paths: int = 25) -> list[str]:
    """Return list of human-readable path strings for the given query.

    Args:
        query: Natural language question.
        hops: Max graph hops. Defaults to settings.graph_hops.
        max_paths: Cap on returned paths to keep prompt size sane.

    Returns:
        List of strings like ``"Elon Musk --FOUNDED--> SpaceX --TARGETS--> Mars"``.
        Empty if the graph isn't configured or no entities matched.
    """
    if not graph_store.is_configured():
        logger.debug("Graph retrieval: graph_store not configured, returning []")
        return []

    h = hops or settings.graph_hops
    entities = extract_entities_from_query(query)
    if not entities:
        logger.debug(f"Graph retrieval: no entities extracted from '{query}'")
        return []

    matched: list[str] = []
    for e in entities:
        canonical = _resolve_to_graph_entity(e)
        if canonical and canonical not in matched:
            matched.append(canonical)

    if not matched:
        logger.debug(f"Graph retrieval: no query entities matched the graph: {entities}")
        return []

    logger.debug(f"Graph retrieval: query entities {entities} → graph entities {matched}")

    paths: list[str] = []
    for entity in matched:
        try:
            for record in graph_store.neighbors(entity, hops=h):
                paths.append(_format_path(record["path"]))
                if len(paths) >= max_paths:
                    break
        except Exception as e:
            logger.warning(f"Graph traversal failed for entity '{entity}': {e}")
        if len(paths) >= max_paths:
            break

    # Dedup while preserving order
    seen = set()
    unique: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    logger.debug(f"Graph retrieval: returning {len(unique)} unique paths")
    return unique
