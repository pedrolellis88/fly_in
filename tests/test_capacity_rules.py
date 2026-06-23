"""Test capacity limits and movement rules."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import build_simulator, run_until_done, write_map


def test_default_link_capacity_allows_one_drone_per_turn(
    tmp_path: Path,
) -> None:
    """Verify that default link capacity allows one drone per turn."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: hub 0 0
        end_hub: goal 1 0
        connection: hub-goal
        """,
    )

    simulator = build_simulator(path)
    first_turn = simulator.next_turn()

    assert len(first_turn) == 1


def test_custom_link_capacity_allows_parallel_drones(
    tmp_path: Path,
) -> None:
    """Verify that max_link_capacity allows parallel movement."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: hub 0 0
        end_hub: goal 1 0
        connection: hub-goal [max_link_capacity=2]
        """,
    )

    simulator = build_simulator(path)
    first_turn = simulator.next_turn()

    assert len(first_turn) == 2


def test_zone_capacity_allows_multiple_drones_inside_zone(
    tmp_path: Path,
) -> None:
    """Verify that max_drones allows multiple drones in one zone."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: hub 0 0
        hub: mid 1 0 [max_drones=2]
        end_hub: goal 2 0
        connection: hub-mid [max_link_capacity=2]
        connection: mid-goal [max_link_capacity=2]
        """,
    )

    simulator = build_simulator(path)
    first_turn = simulator.next_turn()

    assert len(first_turn) == 2
    assert simulator.drones.get_zone(1) == "mid"
    assert simulator.drones.get_zone(2) == "mid"


def test_restricted_zone_takes_two_turns(tmp_path: Path) -> None:
    """Verify that entering a restricted zone takes two turns."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: hub 0 0
        hub: danger 1 0 [zone=restricted]
        end_hub: goal 2 0
        connection: hub-danger
        connection: danger-goal
        """,
    )

    simulator = build_simulator(path)

    turn_1 = simulator.next_turn()
    assert any("hub-danger" in move for move in turn_1)
    assert simulator.drones.is_in_transit(1) is True

    turn_2 = simulator.next_turn()
    assert any("danger" in move for move in turn_2)
    assert simulator.drones.get_zone(1) == "danger"


def test_blocked_zone_is_not_used_when_alternative_exists(
    tmp_path: Path,
) -> None:
    """Verify that blocked zones are avoided when a valid route exists."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: hub 0 0
        hub: blocked 1 0 [zone=blocked]
        hub: safe 1 1
        end_hub: goal 2 0
        connection: hub-blocked
        connection: blocked-goal
        connection: hub-safe
        connection: safe-goal
        """,
    )

    simulator = build_simulator(path)
    history = run_until_done(simulator)

    flattened = " ".join(" ".join(turn) for turn in history)

    assert "blocked" not in flattened
    assert simulator.drones.all_delivered()
