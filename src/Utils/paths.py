"""Helpers for querying ordered paths."""

from __future__ import annotations

from typing import TypeVar

PathItem = TypeVar("PathItem")


def get_path_suffix(
    path: list[PathItem],
    item: PathItem,
) -> list[PathItem] | None:
    """Return the path starting at an item, or None when it is absent."""
    try:
        item_index = path.index(item)
    except ValueError:
        return None

    return path[item_index:]


def get_next_path_item(
    path: list[PathItem],
    item: PathItem,
) -> PathItem | None:
    """Return the item following a path item, or None when unavailable."""
    suffix = get_path_suffix(path, item)

    if suffix is None or len(suffix) < 2:
        return None

    return suffix[1]
