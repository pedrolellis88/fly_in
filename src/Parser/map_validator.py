"""Validation for parsed Fly-in maps."""

from __future__ import annotations

from collections import deque
from typing import Any

from src.Utils.adjacency import build_bidirectional_adjacency

from .declaration_parser import MapParserError


class MapValidator:
    """Validate the final parsed map structure."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate mandatory declarations, references, and reachability."""
        self._validate_required_fields(data)
        self._validate_connection_references(data)

        adjacency = self._build_adjacency(data)
        if not self._is_end_reachable(data, adjacency):
            raise MapParserError(
                f"end_hub {data['end']!r} is not reachable "
                f"from start_hub {data['start']!r}."
            )

    def _validate_required_fields(self, data: dict[str, Any]) -> None:
        """Validate mandatory map declarations."""
        if data["nb_drones"] is None:
            raise MapParserError("Missing nb_drones definition.")
        if data["start"] is None:
            raise MapParserError("Missing start_hub definition.")
        if data["end"] is None:
            raise MapParserError("Missing end_hub definition.")
        if not data["connections"]:
            raise MapParserError("Map must contain at least one connection.")

    def _validate_connection_references(self, data: dict[str, Any]) -> None:
        """Raise if any connection references an undeclared zone."""
        for conn in data["connections"]:
            for zone in (conn["from"], conn["to"]):
                if zone not in data["zones"]:
                    raise MapParserError(
                        f"Line {conn.get('line', '?')}: connection "
                        f"references undefined zone {zone!r}."
                    )

    def _build_adjacency(
        self,
        data: dict[str, Any],
    ) -> dict[str, list[str]]:
        """Build an adjacency list from parsed connections."""
        return build_bidirectional_adjacency(
            data["zones"],
            (
                (connection["from"], connection["to"])
                for connection in data["connections"]
            ),
        )

    def _is_end_reachable(
        self,
        data: dict[str, Any],
        adjacency: dict[str, list[str]],
    ) -> bool:
        """Check whether end_hub is reachable from start_hub via BFS."""
        visited: set[str] = set()
        queue: deque[str] = deque([data["start"]])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue

            visited.add(current)
            queue.extend(
                neighbor
                for neighbor in adjacency[current]
                if neighbor not in visited
            )

        return data["end"] in visited
