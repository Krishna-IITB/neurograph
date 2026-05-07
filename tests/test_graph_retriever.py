"""Unit tests for graph_retriever JSON parser and path formatter."""

from neurograph.retrieval.graph_retriever import _extract_json_list, _format_path


def test_extract_clean_list():
    assert _extract_json_list('["Elon Musk", "Tesla"]') == ["Elon Musk", "Tesla"]


def test_extract_strips_fence():
    raw = '```json\n["A", "B"]\n```'
    assert _extract_json_list(raw) == ["A", "B"]


def test_extract_strips_commentary():
    raw = "Here are the entities: [\"Elon Musk\", \"SpaceX\"]"
    assert _extract_json_list(raw) == ["Elon Musk", "SpaceX"]


def test_extract_handles_garbage():
    assert _extract_json_list("not json") == []
    assert _extract_json_list("") == []
    assert _extract_json_list("[malformed") == []


def test_extract_filters_empty_and_non_strings():
    raw = '["", "  ", "real", null, 42]'
    out = _extract_json_list(raw)
    # null gets dropped, ints get coerced, empties filtered
    assert "real" in out
    assert "" not in out
    assert all(s.strip() for s in out)


def test_format_path_three_node_outgoing():
    segs = [
        {"type": "node", "name": "Elon Musk"},
        {"type": "rel", "name": "FOUNDED", "dir": "out"},
        {"type": "node", "name": "SpaceX"},
        {"type": "rel", "name": "TARGETS", "dir": "out"},
        {"type": "node", "name": "Mars"},
    ]
    assert _format_path(segs) == "Elon Musk --FOUNDED--> SpaceX --TARGETS--> Mars"


def test_format_path_incoming_rel():
    """An incoming rel renders with leftward arrow."""
    segs = [
        {"type": "node", "name": "Tesla"},
        {"type": "rel", "name": "IS_LEADER_OF", "dir": "in"},
        {"type": "node", "name": "Elon Musk"},
    ]
    assert _format_path(segs) == "Tesla <--IS_LEADER_OF-- Elon Musk"


def test_format_path_mixed_directions():
    segs = [
        {"type": "node", "name": "Elon Musk"},
        {"type": "rel", "name": "FOUNDED", "dir": "out"},
        {"type": "node", "name": "SpaceX"},
        {"type": "rel", "name": "IS_LEADER_OF", "dir": "in"},
        {"type": "node", "name": "Elon Musk"},
    ]
    out = _format_path(segs)
    assert "Elon Musk --FOUNDED--> SpaceX" in out
    assert "<--IS_LEADER_OF-- Elon Musk" in out


def test_format_path_single_node():
    assert _format_path([{"type": "node", "name": "A"}]) == "A"
