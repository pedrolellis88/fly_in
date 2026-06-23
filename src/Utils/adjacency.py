"""Helpers for building graph adjacency mappings."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Hashable, TypeVar

Node = TypeVar("Node", bound=Hashable)


def build_bidirectional_adjacency(
    nodes: Iterable[Node],
    edges: Iterable[tuple[Node, Node]],
) -> dict[Node, list[Node]]:
    """Return an adjacency list for a collection of undirected edges."""
    adjacency: dict[Node, list[Node]] = {
        node: [] for node in nodes
    }

    for node_a, node_b in edges:
        adjacency[node_a].append(node_b)
        adjacency[node_b].append(node_a)

    return adjacency
