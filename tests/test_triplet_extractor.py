"""Unit tests for triplet_extractor — focuses on defensive JSON parsing
since the LLM call itself is integration-level."""

from neurograph.indexing.triplet_extractor import (
    Triplet,
    _extract_json_array,
    _normalize_relation,
)


def test_extract_clean_json():
    raw = '[{"head": "A", "relation": "X", "tail": "B"}]'
    assert _extract_json_array(raw) == [{"head": "A", "relation": "X", "tail": "B"}]


def test_extract_strips_markdown_fence():
    raw = '```json\n[{"head": "A", "relation": "X", "tail": "B"}]\n```'
    assert len(_extract_json_array(raw)) == 1


def test_extract_strips_commentary():
    raw = 'Sure, here are the triplets:\n[{"head": "A", "relation": "X", "tail": "B"}]\nLet me know if you need more.'
    assert len(_extract_json_array(raw)) == 1


def test_extract_returns_empty_on_garbage():
    assert _extract_json_array("not json at all") == []


def test_extract_returns_empty_on_invalid_json():
    assert _extract_json_array("[not, valid, json]") == []


def test_extract_handles_empty_input():
    assert _extract_json_array("") == []


def test_normalize_relation_uppercases():
    assert _normalize_relation("ceo of") == "CEO_OF"


def test_normalize_relation_strips_special():
    assert _normalize_relation("works-at!") == "WORKSAT"


def test_normalize_relation_collapses_underscores():
    assert _normalize_relation("CEO__of___tesla") == "CEO_OF_TESLA"


def test_normalize_relation_falls_back():
    assert _normalize_relation("!@#") == "RELATED_TO"


def test_triplet_validates_min_length():
    """Pydantic should reject empty strings."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Triplet(head="", relation="X", tail="B")
