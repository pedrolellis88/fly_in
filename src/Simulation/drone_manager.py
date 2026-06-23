"""Manage drone state for the Fly-in simulation."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from src.Utils.drone_ids import iter_drone_ids


@dataclass
class DroneState:
    """Store all mutable state related to a single drone."""

    zone: str | None
    in_transit: bool = False
    target_zone: str | None = None
    remaining_turns: int = 0
    connection_label: str | None = None
    connection_key: frozenset[str] | None = None
    wait_turns: int = 0
    current_path: list[str] | None = None
    path_version: int = 0
    delivered: bool = False
    history: list[str] = field(default_factory=list)


class DroneManager:
    """Store and update all drone states during the simulation."""

    def __init__(self, nb_drones: int, start_zone: str) -> None:
        """Initialize all drones at the start zone."""
        self.nb_drones = nb_drones
        self.start_zone = start_zone
        self.states: dict[int, DroneState] = {}
        self._initialize_drones()

    def _initialize_drones(self) -> None:
        """Place every drone at the start zone with a clean state."""
        for drone_id in iter_drone_ids(self.nb_drones):
            self.states[drone_id] = DroneState(
                zone=self.start_zone,
                history=[self.start_zone],
            )

    def _get_state(self, drone_id: int) -> DroneState:
        """Return the state object for one drone."""
        return self.states[drone_id]

    def capture_states(self) -> dict[int, DroneState]:
        """Return an independent copy of every drone state."""
        return copy.deepcopy(self.states)

    def restore_states(self, states: dict[int, DroneState]) -> None:
        """Replace all drone states with an independent snapshot copy."""
        self.states = copy.deepcopy(states)

    @property
    def delivered(self) -> set[int]:
        """Return the IDs of all delivered drones."""
        return {
            drone_id
            for drone_id, state in self.states.items()
            if state.delivered
        }

    def is_delivered(self, drone_id: int) -> bool:
        """Return whether the drone has reached the end zone."""
        return self._get_state(drone_id).delivered

    def mark_delivered(self, drone_id: int) -> None:
        """Mark a drone as delivered."""
        self._get_state(drone_id).delivered = True

    def all_delivered(self) -> bool:
        """Return whether all drones have reached the end zone."""
        return len(self.delivered) == self.nb_drones

    def is_in_transit(self, drone_id: int) -> bool:
        """Return whether the drone is currently between two zones."""
        return self._get_state(drone_id).in_transit

    def get_zone(self, drone_id: int) -> str | None:
        """Return the current zone of a drone.

        Return None when the drone is in transit.
        """
        return self._get_state(drone_id).zone

    def get_wait_turns(self, drone_id: int) -> int:
        """Return how many consecutive turns the drone has waited."""
        return self._get_state(drone_id).wait_turns

    def get_current_path(self, drone_id: int) -> list[str] | None:
        """Return the path currently assigned to a drone."""
        return self._get_state(drone_id).current_path

    def set_current_path(self, drone_id: int, path: list[str]) -> None:
        """Assign a path to a drone and update its path version."""
        state = self._get_state(drone_id)
        state.current_path = path
        state.path_version += 1

    def start_transit(
        self,
        drone_id: int,
        target_zone: str,
        remaining_turns: int,
        connection_label: str,
        connection_key: frozenset[str],
    ) -> None:
        """Move a drone into a transit state."""
        state = self._get_state(drone_id)
        state.zone = None
        state.in_transit = True
        state.target_zone = target_zone
        state.remaining_turns = remaining_turns
        state.connection_label = connection_label
        state.connection_key = connection_key
        state.wait_turns = 0

    def finish_transit(self, drone_id: int, target_zone: str) -> None:
        """Move a transit drone into its target zone."""
        state = self._get_state(drone_id)
        state.zone = target_zone
        state.in_transit = False
        state.target_zone = None
        state.remaining_turns = 0
        state.connection_label = None
        state.connection_key = None
        state.wait_turns = 0

    def move_to_zone(self, drone_id: int, zone_name: str) -> None:
        """Move a drone directly to a zone and reset its wait counter."""
        state = self._get_state(drone_id)
        state.zone = zone_name
        state.wait_turns = 0

    def decrease_transit_turn(self, drone_id: int) -> None:
        """Decrease the remaining transit time by one turn."""
        self._get_state(drone_id).remaining_turns -= 1

    def get_remaining_turns(self, drone_id: int) -> int:
        """Return remaining turns for a drone in transit."""
        return self._get_state(drone_id).remaining_turns

    def get_target_zone(self, drone_id: int) -> str | None:
        """Return the target zone of a drone in transit."""
        return self._get_state(drone_id).target_zone

    def get_connection_label(self, drone_id: int) -> str | None:
        """Return the display label of the transit connection."""
        return self._get_state(drone_id).connection_label

    def get_connection_key(self, drone_id: int) -> frozenset[str] | None:
        """Return the unordered key of the transit connection."""
        return self._get_state(drone_id).connection_key

    def increase_wait_turns(self, drone_id: int) -> None:
        """Increase the drone wait counter by one turn."""
        self._get_state(drone_id).wait_turns += 1
