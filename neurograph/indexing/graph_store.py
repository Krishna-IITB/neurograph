"""Neo4j wrapper for the knowledge graph."""

from __future__ import annotations

import re
from functools import lru_cache

from loguru import logger
from neo4j import GraphDatabase
from tqdm import tqdm

from neurograph.config import settings
from neurograph.indexing.cypher_builder import build_merge_query
from neurograph.indexing.triplet_extractor import Triplet


class _GraphStore:
    def __init__(self) -> None:
        if not settings.neo4j_uri or not settings.neo4j_password:
            raise RuntimeError(
                "Neo4j credentials missing — set NEO4J_URI and NEO4J_PASSWORD in .env"
            )
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        # Sanity check the connection
        with self._driver.session() as s:
            s.run("RETURN 1").single()
        logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")

    def upsert(self, triplets: list[Triplet], batch_size: int = 100) -> None:
        if not triplets:
            return
        with self._driver.session() as session:
            for t in tqdm(triplets, desc="Writing to Neo4j", unit="triplet"):
                cypher, params = build_merge_query(t)
                session.run(cypher, params)
        logger.info(f"Wrote {len(triplets)} triplets to Neo4j")

    def neighbors(self, entity: str, hops: int | None = None) -> list[dict]:
        """Return all paths up to `hops` length from `entity`.

        Each path is returned as a list of segments with correct direction:
            [
                {"type": "node", "name": "Elon Musk"},
                {"type": "rel",  "name": "FOUNDED", "dir": "out"},
                {"type": "node", "name": "SpaceX"},
                {"type": "rel",  "name": "IS_LEADER_OF", "dir": "in"},
                {"type": "node", "name": "Elon Musk"},
            ]
        `dir="out"` means the relationship points from the previous node
        to the next; `dir="in"` means the previous node is the target.
        """
        h = int(hops or settings.graph_hops)
        if not (1 <= h <= 5):
            raise ValueError(f"hops must be 1..5, got {h}")

        cypher = (
            f"MATCH path = (start:Entity {{name: $name}})-[*1..{h}]-(end) "
            f"RETURN path LIMIT 50"
        )
        out: list[dict] = []
        with self._driver.session() as session:
            for record in session.run(cypher, name=entity):
                path = record["path"]
                segments: list[dict] = []
                nodes = list(path.nodes)
                rels = list(path.relationships)
                for i, node in enumerate(nodes):
                    segments.append({"type": "node", "name": node.get("name", "?")})
                    if i < len(rels):
                        rel = rels[i]
                        # Determine direction: if the rel starts at the current node,
                        # we're traversing forward. Otherwise it's backward.
                        direction = "out" if rel.start_node.element_id == node.element_id else "in"
                        segments.append({"type": "rel", "name": rel.type, "dir": direction})
                out.append({"path": segments})
        return out

    def stats(self) -> dict:
        cypher = (
            "MATCH (n:Entity) WITH count(n) AS nodes "
            "MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
        )
        with self._driver.session() as session:
            record = session.run(cypher).single()
            return dict(record) if record else {"nodes": 0, "rels": 0}

    def reset(self) -> None:
        """Wipe all nodes and relationships. Dev only."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("Neo4j graph wiped")

    def close(self) -> None:
        self._driver.close()


@lru_cache(maxsize=1)
def _store() -> _GraphStore:
    return _GraphStore()


# Public API ----------------------------------------------------------------


def upsert_triplets(triplets: list[Triplet]) -> None:
    _store().upsert(triplets)


def neighbors(entity: str, hops: int | None = None) -> list[dict]:
    return _store().neighbors(entity, hops)


def stats() -> dict:
    return _store().stats()


def reset() -> None:
    _store().reset()


def is_configured() -> bool:
    return bool(settings.neo4j_uri and settings.neo4j_password)
