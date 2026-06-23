"""Provide shared test helpers for Fly-in."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.Models.graph import Graph
from src.Parser.map_parser import MapParser
from src.Simulation.simulator import Simulator


@pytest.fixture
def valid_maps_dir() -> Path:
    """Return the directory containing valid test maps."""
    return Path("maps/valid")


def write_map(tmp_path: Path, content: str) -> Path:
    """Create a temporary map file with the given content."""
    path = tmp_path / "test_map.txt"
    path.write_text(content.strip() + "\n")
    return path


def build_graph(path: Path) -> Graph:
    """Build a graph from a map file."""
    parser = MapParser()
    parsed_map = parser.parse(path)
    return Graph.from_parsed_data(parsed_map)


def build_simulator(path: Path) -> Simulator:
    """Build a simulator from a map file."""
    return Simulator(build_graph(path))


def run_until_done(
    simulator: Simulator,
    max_turns: int = 200,
) -> list[list[str]]:
    """Run a simulator until all drones are delivered.

    Raise:
        AssertionError: If the simulation exceeds max_turns.
    """
    history: list[list[str]] = []

    while not simulator.drones.all_delivered():
        if len(history) >= max_turns:
            raise AssertionError("Simulation exceeded max_turns")

        history.append(simulator.next_turn())

    return history
