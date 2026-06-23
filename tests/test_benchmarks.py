"""Run performance smoke tests for valid Fly-in maps."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import build_simulator, run_until_done


@pytest.mark.parametrize(
    ("map_name", "max_turns"),
    [
        ("easy_map_01.txt", 20),
        ("link_capacity_map.txt", 20),
        ("multi_path_map.txt", 25),
        ("benchmark_linear_6.txt", 25),
        ("benchmark_simple_fork_8.txt", 35),
        ("benchmark_capacity_hell_12.txt", 80),
    ],
)
def test_maps_finish_under_reasonable_turn_limit(
    valid_maps_dir: Path,
    map_name: str,
    max_turns: int,
) -> None:
    """Verify that provided maps finish within safe turn limits."""
    simulator = build_simulator(valid_maps_dir / map_name)
    history = run_until_done(simulator, max_turns=max_turns)

    assert len(history) <= max_turns
    assert simulator.drones.all_delivered()
