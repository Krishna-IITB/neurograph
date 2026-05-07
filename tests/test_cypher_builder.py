"""Unit tests for cypher_builder — pure functions, no DB needed."""

from neurograph.indexing.cypher_builder import build_merge_query
from neurograph.indexing.triplet_extractor import Triplet


def test_basic_merge_query():
    t = Triplet(head="Elon Musk", relation="CEO_OF", tail="Tesla", source_chunk_id="t:p1:c0")
    cypher, params = build_merge_query(t)
    assert "MERGE" in cypher
    assert "[r:CEO_OF]" in cypher
    assert params == {"head": "Elon Musk", "tail": "Tesla", "source_chunk_id": "t:p1:c0"}


def test_relation_normalized():
    t = Triplet(head="A", relation="ceo of", tail="B")
    cypher, _ = build_merge_query(t)
    assert "[r:CEO_OF]" in cypher


def test_relation_strips_special_chars():
    t = Triplet(head="A", relation="works-at!", tail="B")
    cypher, _ = build_merge_query(t)
    assert "[r:WORKSAT]" in cypher


def test_relation_starting_with_digit_gets_prefixed():
    t = Triplet(head="A", relation="2nd in command", tail="B")
    cypher, _ = build_merge_query(t)
    # Cypher identifiers can't start with a digit
    assert "[r:REL_" in cypher


def test_empty_relation_falls_back():
    t = Triplet(head="A", relation="!@#$", tail="B")
    cypher, _ = build_merge_query(t)
    assert "RELATED_TO" in cypher


def test_uses_merge_not_create():
    """Critical for idempotency."""
    t = Triplet(head="A", relation="X", tail="B")
    cypher, _ = build_merge_query(t)
    assert cypher.count("MERGE") == 3  # head, tail, relationship
    assert "CREATE" not in cypher
