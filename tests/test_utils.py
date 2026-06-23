"""Test shared utility helpers."""

from __future__ import annotations

from src.Utils import adjust_count
from src.Utils import append_to_group
from src.Utils import build_bidirectional_adjacency
from src.Utils import get_next_path_item
from src.Utils import get_path_suffix


def test_build_bidirectional_adjacency_keeps_isolated_nodes() -> None:
    """Build both edge directions without dropping isolated nodes."""
    adjacency = build_bidirectional_adjacency(
        ["a", "b", "isolated"],
        [("a", "b")],
    )

    assert adjacency == {
        "a": ["b"],
        "b": ["a"],
        "isolated": [],
    }


def test_adjust_count_supports_positive_and_negative_changes() -> None:
    """Update existing and missing counters through one helper."""
    counts = {"used": 2}

    assert adjust_count(counts, "used", -1) == 1
    assert adjust_count(counts, "new") == 1
    assert counts == {"used": 1, "new": 1}


def test_append_to_group_initializes_and_reuses_group() -> None:
    """Append values while preserving insertion order."""
    groups: dict[str, list[int]] = {}

    append_to_group(groups, "zone", 2)
    append_to_group(groups, "zone", 1)

    assert groups == {"zone": [2, 1]}


def test_path_helpers_handle_present_missing_and_final_items() -> None:
    """Query path continuations without repeated index handling."""
    path = ["start", "middle", "end"]

    assert get_path_suffix(path, "middle") == ["middle", "end"]
    assert get_path_suffix(path, "missing") is None
    assert get_next_path_item(path, "middle") == "end"
    assert get_next_path_item(path, "end") is None
