"""Test general simulation behavior."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import build_simulator, run_until_done


def test_all_drones_start_at_start_zone(valid_maps_dir: Path) -> None:
    """Verify that all drones start at the start zone."""
    simulator = build_simulator(valid_maps_dir / "easy_map_01.txt")

    for drone_id in range(1, simulator.nb_drones + 1):
        assert simulator.drones.get_zone(drone_id) == simulator.graph.start
        assert simulator.drones.is_in_transit(drone_id) is False


def test_easy_map_reaches_goal(valid_maps_dir: Path) -> None:
    """Verify that a simple map finishes successfully."""
    simulator = build_simulator(valid_maps_dir / "easy_map_01.txt")
    history = run_until_done(simulator)

    assert history
    assert simulator.drones.all_delivered()


def test_stationary_drones_are_omitted_from_output(
    valid_maps_dir: Path,
) -> None:
    """Verify that turn output includes only moving drones."""
    simulator = build_simulator(valid_maps_dir / "easy_map_01.txt")
    history = run_until_done(simulator)

    for turn in history:
        for movement in turn:
            assert movement.startswith("D")
            assert "-" in movement


def test_multiple_paths_are_available(valid_maps_dir: Path) -> None:
    """Verify that multi-path maps expose multiple available paths."""
    simulator = build_simulator(valid_maps_dir / "multi_path_map.txt")

    assert len(simulator.get_available_paths()) >= 2
