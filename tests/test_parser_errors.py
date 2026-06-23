"""Test parser validation rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.Parser.map_parser import MapParser, MapParserError
from tests.conftest import build_graph, write_map


def test_parser_accepts_valid_basic_map(tmp_path: Path) -> None:
    """Verify that the parser accepts a minimal valid map."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: hub 0 0
        end_hub: goal 2 0
        connection: hub-goal
        """,
    )

    graph = build_graph(path)

    assert graph.nb_drones == 2
    assert graph.start == "hub"
    assert graph.end == "goal"


def test_parser_ignores_comments(tmp_path: Path) -> None:
    """Verify that the parser ignores full-line and inline comments."""
    path = write_map(
        tmp_path,
        """
        # comment before drone count
        nb_drones: 1

        start_hub: hub 0 0 # inline comment
        end_hub: goal 2 0
        connection: hub-goal
        """,
    )

    graph = build_graph(path)

    assert graph.nb_drones == 1
    assert "hub" in graph.zones
    assert "goal" in graph.zones


def test_parser_rejects_missing_drone_count(tmp_path: Path) -> None:
    """Verify that the parser rejects files without nb_drones."""
    path = write_map(
        tmp_path,
        """
        start_hub: hub 0 0
        end_hub: goal 2 0
        connection: hub-goal
        """,
    )

    with pytest.raises(MapParserError):
        MapParser().parse(path)


def test_parser_rejects_invalid_zone_type(tmp_path: Path) -> None:
    """Verify that the parser rejects invalid zone metadata."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: hub 0 0
        hub: x 1 0 [zone=banana]
        end_hub: goal 2 0
        connection: hub-x
        connection: x-goal
        """,
    )

    with pytest.raises(MapParserError):
        MapParser().parse(path)


def test_parser_rejects_duplicate_connection(tmp_path: Path) -> None:
    """Verify that the parser rejects duplicate bidirectional connections."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: hub 0 0
        end_hub: goal 2 0
        connection: hub-goal
        connection: goal-hub
        """,
    )

    with pytest.raises(MapParserError):
        MapParser().parse(path)


def test_parser_rejects_connection_before_zone_declarations(
    tmp_path: Path,
) -> None:
    """Verify that connection endpoints must already be declared."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        connection: hub-goal
        start_hub: hub 0 0
        end_hub: goal 2 0
        """,
    )

    with pytest.raises(
        MapParserError,
        match="Line 2: connection references undefined zone 'hub'",
    ):
        MapParser().parse(path)


def test_parser_rejects_non_positive_capacity(tmp_path: Path) -> None:
    """Verify that the parser rejects non-positive zone capacities."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: hub 0 0
        hub: a 1 0 [max_drones=0]
        end_hub: goal 2 0
        connection: hub-a
        connection: a-goal
        """,
    )

    with pytest.raises(MapParserError):
        MapParser().parse(path)
