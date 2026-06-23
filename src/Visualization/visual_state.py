"""Provide visual state helpers for the Fly-in renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from src.Simulation.drone_manager import DroneState
from src.Simulation.simulator import Simulator
from src.Utils.drone_ids import iter_drone_ids
from src.Utils.mappings import append_to_group

Position: TypeAlias = tuple[float, float]
DronePositions: TypeAlias = dict[int, Position | None]
DroneStatus: TypeAlias = Literal["waiting", "flying", "done"]
DroneStatuses: TypeAlias = dict[int, DroneStatus]


@dataclass
class RendererSnapshot:
    """Store a restorable snapshot of simulator and drone state."""

    turn: int
    drone_states: dict[int, DroneState]


class VisualStateManager:
    """Capture, restore, and derive visual simulation state."""

    def capture(self, simulator: Simulator) -> RendererSnapshot:
        """Return a deep snapshot of the current simulator state.

        The snapshot is used by the renderer to restore previous turns during
        backward navigation without sharing mutable state with the simulator.
        """
        drones = simulator.drones

        return RendererSnapshot(
            turn=simulator.turn,
            drone_states=drones.capture_states(),
        )

    def restore(
        self,
        simulator: Simulator,
        snapshot: RendererSnapshot,
    ) -> None:
        """Restore simulator and drone state from a snapshot.

        Snapshot data is copied back into the simulator to avoid keeping
        references to mutable snapshot internals.
        """
        drones = simulator.drones

        simulator.turn = snapshot.turn
        drones.restore_states(snapshot.drone_states)

    def group_drones_by_zone(
        self,
        simulator: Simulator,
    ) -> dict[str, list[int]]:
        """Return drones grouped by the zones they currently occupy.

        Delivered drones and drones in transit are excluded because they are
        not visually grouped around a zone center.
        """
        groups: dict[str, list[int]] = {}
        drones = simulator.drones

        for drone_id in iter_drone_ids(drones.nb_drones):
            if drones.is_delivered(drone_id):
                continue
            if drones.is_in_transit(drone_id):
                continue

            zone_name = drones.get_zone(drone_id)
            if zone_name is None:
                continue

            append_to_group(groups, zone_name, drone_id)

        return groups
