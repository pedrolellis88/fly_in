"""Provide helpers for bidirectional connection keys."""

from __future__ import annotations


def make_connection_key(zone_a: str, zone_b: str) -> frozenset[str]:
    """Create an unordered key for a bidirectional connection."""
    return frozenset({zone_a, zone_b})
