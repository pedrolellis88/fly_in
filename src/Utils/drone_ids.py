"""Helpers for drone id iteration."""

from __future__ import annotations


def iter_drone_ids(nb_drones: int) -> range:
    """Return the valid drone id range used by the project."""
    return range(1, nb_drones + 1)
