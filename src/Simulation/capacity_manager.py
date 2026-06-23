"""Manage capacity usage and resolve movement conflicts."""

from __future__ import annotations

from dataclasses import dataclass

from src.Models.graph import Connection
from src.Models.graph import Graph
from src.Simulation.drone_manager import DroneManager
from src.Utils.connection_key import make_connection_key
from src.Utils.drone_ids import iter_drone_ids
from src.Utils.mappings import adjust_count


@dataclass(frozen=True)
class MoveIntent:
    """Represent one requested drone movement before approval."""

    drone_id: int
    from_zone: str
    to_zone: str
    connection: Connection
    is_restricted: bool
    zone_type: str
    remaining_cost: float
    wait_turns: int


TransitArrival = tuple[int, str]


class CapacityManager:
    """Compute usage and approve movements within capacity limits."""

    def __init__(self, graph: Graph, drones: DroneManager) -> None:
        """Initialize capacity manager."""
        self.graph = graph
        self.drones = drones

    def compute_zone_occupancy(self) -> dict[str, int]:
        """Return current zone occupancy."""
        occupancy = {zone_name: 0 for zone_name in self.graph.zones}

        for drone_id in iter_drone_ids(self.drones.nb_drones):
            if self.drones.is_delivered(drone_id):
                continue

            if self.drones.is_in_transit(drone_id):
                continue

            current_zone = self.drones.get_zone(drone_id)

            if current_zone is None:
                continue

            adjust_count(occupancy, current_zone)

        return occupancy

    def compute_link_usage(self) -> dict[frozenset[str], int]:
        """Return current connection usage."""
        usage: dict[frozenset[str], int] = {}

        for drone_id in iter_drone_ids(self.drones.nb_drones):
            if self.drones.is_delivered(drone_id):
                continue

            if not self.drones.is_in_transit(drone_id):
                continue

            if self.drones.get_remaining_turns(drone_id) <= 1:
                continue

            connection_key = self.drones.get_connection_key(drone_id)

            if connection_key is None:
                continue

            adjust_count(usage, connection_key)

        return usage

    def resolve_intents(
        self,
        intents: list[MoveIntent],
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
    ) -> list[MoveIntent]:
        """Approve movement intents without violating capacities."""
        approved: list[MoveIntent] = []
        reserved_zone_entries: dict[str, int] = {}
        reserved_zone_exits: dict[str, int] = {}
        reserved_link_usage: dict[frozenset[str], int] = {}

        for intent in sorted(intents, key=self._intent_priority_key):
            if self._should_reject_intent(
                intent,
                zone_occupancy,
                link_usage,
                reserved_zone_entries,
                reserved_zone_exits,
                reserved_link_usage,
            ):
                continue

            approved.append(intent)
            self._reserve_intent(
                intent,
                reserved_zone_entries,
                reserved_zone_exits,
                reserved_link_usage,
            )

        return approved

    def _should_reject_intent(
        self,
        intent: MoveIntent,
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
        reserved_zone_entries: dict[str, int],
        reserved_zone_exits: dict[str, int],
        reserved_link_usage: dict[frozenset[str], int],
    ) -> bool:
        """Return whether an intent violates capacity constraints."""
        if intent.from_zone == intent.to_zone:
            return True

        connection_key = make_connection_key(
            intent.connection.zone_a,
            intent.connection.zone_b,
        )
        current_link_usage = (
            link_usage.get(connection_key, 0)
            + reserved_link_usage.get(connection_key, 0)
        )

        if current_link_usage >= intent.connection.max_link_capacity:
            return True

        if intent.to_zone in (self.graph.start, self.graph.end):
            return False

        target_capacity = self.graph.get_zone_capacity(intent.to_zone)
        current_zone_usage = (
            zone_occupancy.get(intent.to_zone, 0)
            - reserved_zone_exits.get(intent.to_zone, 0)
            + reserved_zone_entries.get(intent.to_zone, 0)
        )
        return current_zone_usage >= target_capacity

    def _reserve_intent(
        self,
        intent: MoveIntent,
        reserved_zone_entries: dict[str, int],
        reserved_zone_exits: dict[str, int],
        reserved_link_usage: dict[frozenset[str], int],
    ) -> None:
        """Reserve capacity for an approved intent."""
        connection_key = make_connection_key(
            intent.connection.zone_a,
            intent.connection.zone_b,
        )
        adjust_count(reserved_link_usage, connection_key)
        adjust_count(reserved_zone_entries, intent.to_zone)

        if intent.from_zone != self.graph.start:
            adjust_count(reserved_zone_exits, intent.from_zone)

    def _intent_priority_key(
        self,
        intent: MoveIntent,
    ) -> tuple[int, float, int, int, int, int]:
        """Return the current deterministic movement priority key."""
        zone_priority_rank = 0 if intent.zone_type == "priority" else 1
        start_departure_penalty = (
            0 if intent.from_zone != self.graph.start else 1
        )
        restricted_penalty = (
            0 if intent.zone_type != "restricted" else 1
        )

        return (
            start_departure_penalty,
            intent.remaining_cost,
            zone_priority_rank,
            restricted_penalty,
            -intent.wait_turns,
            intent.drone_id,
        )
