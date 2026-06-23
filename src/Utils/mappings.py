"""Small helpers for mutable mapping updates."""

from __future__ import annotations

from typing import Hashable, TypeVar

Key = TypeVar("Key", bound=Hashable)
Value = TypeVar("Value")


def adjust_count(
    counts: dict[Key, int],
    key: Key,
    amount: int = 1,
) -> int:
    """Adjust a counter value and return the updated count."""
    updated_count = counts.get(key, 0) + amount
    counts[key] = updated_count
    return updated_count


def append_to_group(
    groups: dict[Key, list[Value]],
    key: Key,
    value: Value,
) -> None:
    """Append a value to a list stored under a mapping key."""
    groups.setdefault(key, []).append(value)
