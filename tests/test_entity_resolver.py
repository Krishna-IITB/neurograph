"""Unit tests for entity resolver — pure rapidfuzz logic."""

from neurograph.indexing.entity_resolver import canonicalize, resolve_triplets
from neurograph.indexing.triplet_extractor import Triplet


def test_empty_known_returns_input():
    assert canonicalize("Tesla", []) == "Tesla"


def test_close_match_canonicalizes():
    # "Tesla Inc" should match existing canonical "Tesla"
    assert canonicalize("Tesla Inc", ["Tesla"]) == "Tesla"


def test_distant_string_stays_unchanged():
    # "Apple" should NOT match "Tesla"
    assert canonicalize("Apple", ["Tesla"]) == "Apple"


def test_typo_collapses():
    # Single-character typo
    assert canonicalize("Tesal", ["Tesla"], threshold=80) == "Tesla"


def test_threshold_rejects_unrelated_strings():
    # token_set_ratio is subset-aware (so "Tesla" / "Tesla Inc" merges by design),
    # but truly unrelated strings should still be rejected at the default threshold.
    assert canonicalize("Apple Inc", ["Tesla Motors"], threshold=90) == "Apple Inc"
    assert canonicalize("Microsoft", ["Tesla"], threshold=90) == "Microsoft"


def test_resolve_triplets_dedups_entities():
    triplets = [
        Triplet(head="Tesla", relation="LOCATED_IN", tail="California"),
        Triplet(head="Tesla Inc", relation="MAKES", tail="Cars"),
        Triplet(head="Tesla Motors", relation="OWNS", tail="Gigafactory"),
    ]
    out = resolve_triplets(triplets, threshold=85)
    # All three head entities should now share the same canonical name
    heads = {t.head for t in out}
    assert len(heads) == 1, f"Expected 1 canonical, got {heads}"


def test_resolve_preserves_relation_and_chunk_id():
    triplets = [
        Triplet(
            head="Tesla", relation="CEO_OF", tail="Elon Musk",
            source_chunk_id="t:p1:c0",
        ),
    ]
    out = resolve_triplets(triplets)
    assert out[0].relation == "CEO_OF"
    assert out[0].source_chunk_id == "t:p1:c0"
