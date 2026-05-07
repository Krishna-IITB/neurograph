"""Unit tests for eval metric pure functions — no LLM calls."""

import pytest
from langchain_core.documents import Document

from neurograph.eval.generation_metrics import _parse_score
from neurograph.eval.retrieval_metrics import (
    average,
    keyword_recall,
    keyword_recall_for_chunks,
    keyword_recall_for_paths,
)


# ---------- retrieval_metrics ----------


def test_keyword_recall_exact_phrase_match():
    """All content tokens of expected appear in retrieved → recall=1.0."""
    assert keyword_recall(
        "Tesla was founded in 2003 by Eberhard.",
        "Tesla was founded in 2003",
    ) == 1.0


def test_keyword_recall_paraphrased_match():
    """Tokens spread across the chunk in different order → still 1.0."""
    big = "founded not by Elon Musk but by Eberhard and Tarpenning in July 2003 — Tesla, Inc..."
    # Content tokens of expected: tesla, founded, july, 2003 — all present
    assert keyword_recall(big, "Tesla was founded in July 2003.") == 1.0


def test_keyword_recall_partial_match_below_threshold():
    """Only some tokens present → below threshold → 0.0."""
    # Expected: "Pretoria South Africa" (3 content tokens). Only 1 present.
    assert keyword_recall(
        "Born in some city.",
        "Pretoria South Africa",
        threshold=0.5,
    ) == 0.0


def test_keyword_recall_miss_completely():
    assert keyword_recall("Apple makes iPhones.", "Tesla was founded in 2003") == 0.0


def test_keyword_recall_empty_inputs():
    assert keyword_recall("", "expected") == 0.0
    assert keyword_recall("retrieved", "") == 0.0


def test_keyword_recall_for_chunks():
    chunks = [
        Document(page_content="Hello world", metadata={}),
        Document(page_content="Tesla was founded in 2003 in California by Eberhard.", metadata={}),
    ]
    assert keyword_recall_for_chunks(chunks, "Tesla was founded in 2003") == 1.0


def test_keyword_recall_for_chunks_empty():
    assert keyword_recall_for_chunks([], "anything") == 0.0


def test_keyword_recall_for_paths_match():
    """Graph paths still get token-matched. UPPERCASE_SNAKE_CASE relations
    tokenize as lowercase content words ('founded' for FOUNDED)."""
    paths = [
        "Elon Musk --FOUNDED--> SpaceX",
        "Tesla --IS_LEADER_OF--> Elon Musk",
    ]
    # Expected tokens: musk, founded, spacex — all present in paths
    assert keyword_recall_for_paths(paths, "Elon Musk founded SpaceX") == 1.0


def test_keyword_recall_for_paths_unrelated_misses():
    paths = ["Tesla --IS_LEADER_OF--> Elon Musk"]
    # Expected tokens: paypal, acquired, ebay — none present
    assert keyword_recall_for_paths(paths, "PayPal was acquired by eBay") == 0.0


def test_keyword_recall_for_paths_empty():
    assert keyword_recall_for_paths([], "anything") == 0.0


def test_average():
    assert average([1.0, 0.0, 1.0]) == pytest.approx(0.6667, rel=1e-3)
    assert average([5.0]) == 5.0
    assert average([]) == 0.0


# ---------- generation_metrics._parse_score ----------


def test_parse_score_clean_digit():
    assert _parse_score("4") == 4.0


def test_parse_score_with_text():
    assert _parse_score("Score: 5") == 5.0
    assert _parse_score("The answer is 3 out of 5") == 3.0


def test_parse_score_invalid():
    assert _parse_score("") == 0.0
    assert _parse_score("nope") == 0.0


def test_parse_score_out_of_range_picks_first_valid():
    """If the LLM emits '7 out of 5', we should pick the first 1-5 digit (none here)."""
    # No digit in 1..5 range
    assert _parse_score("7") == 0.0
    # Has a 5 later
    assert _parse_score("7 (max 5)") == 5.0
