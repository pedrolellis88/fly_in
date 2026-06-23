"""Run the turn-based simulation engine for the Fly-in project."""

from __future__ import annotations

from src.Models.graph import Graph
from src.Simulation.capacity_manager import CapacityManager, MoveIntent
from src.Simulation.capacity_manager import TransitArrival
from src.Simulation.drone_manager import DroneManager
from src.Simulation.route_manager import RouteManager
from src.Utils.connection_key import make_connection_key
from src.Utils.drone_ids import iter_drone_ids
from src.Utils.mappings import adjust_count


class Simulator:
    """Coordinate drone movement through the graph turn by turn."""

    def __init__(self, graph: Graph) -> None:
        """Initialize the simulator."""
        self.graph = graph
        self.nb_drones = graph.nb_drones
        self.start_zone = graph.start
        self.end_zone = graph.end
        self.turn = 0

        self.drones = DroneManager(
            nb_drones=self.nb_drones,
            start_zone=self.start_zone,
        )
        self.capacity = CapacityManager(self.graph, self.drones)
        self.routes = RouteManager(self.graph, self.drones)

    def run(self) -> None:
        """Run the simulation until every drone is delivered or blocked."""
        while not self.drones.all_delivered():
            movements = self.next_turn()

            if not movements:
                print(f"Turn {self.turn}: no movement possible.")
                break

            print(" ".join(movements))

    def next_turn(self) -> list[str]:
        """Advance the simulation by one public turn."""
        if self.drones.all_delivered():
            return []

        self.turn += 1
        return self._simulate_turn()

    def get_available_paths(self) -> list[list[str]]:
        """Return the paths available to the route manager."""
        return self.routes.available_paths

    def _simulate_turn(self) -> list[str]:
        """Simulate one full turn of drone movement."""
        movements: list[str] = []
        processed_drones: set[int] = set()

        zone_occupancy = self.capacity.compute_zone_occupancy()
        link_usage = self.capacity.compute_link_usage()

        arrivals = self._advance_transit_drones(
            movements,
            processed_drones,
        )

        intents = self._collect_move_intents(
            processed_drones,
            zone_occupancy,
            link_usage,
        )

        approved_intents = self.capacity.resolve_intents(
            intents,
            zone_occupancy,
            link_usage,
        )

        self._apply_move_intents(
            approved_intents,
            movements,
            zone_occupancy,
            link_usage,
            processed_drones,
        )

        self._apply_transit_arrivals(
            arrivals,
            movements,
            zone_occupancy,
            processed_drones,
        )

        self._update_wait_counters(processed_drones)

        return movements

    def _advance_transit_drones(
        self,
        movements: list[str],
        processed_drones: set[int],
    ) -> list[TransitArrival]:
        """Advance drones already moving through restricted connections."""
        arrivals: list[TransitArrival] = []

        for drone_id in iter_drone_ids(self.nb_drones):
            if self.drones.is_delivered(drone_id):
                continue

            if not self.drones.is_in_transit(drone_id):
                continue

            self.drones.decrease_transit_turn(drone_id)

            if self.drones.get_remaining_turns(drone_id) > 0:
                self._record_transit_progress(
                    drone_id,
                    movements,
                    processed_drones,
                )
                continue

            target_zone = self.drones.get_target_zone(drone_id)

            if target_zone is None:
                raise RuntimeError("Transit drone has no target zone.")

            arrivals.append((drone_id, target_zone))
            processed_drones.add(drone_id)

        return arrivals

    def _record_transit_progress(
        self,
        drone_id: int,
        movements: list[str],
        processed_drones: set[int],
    ) -> None:
        """Record movement output for a drone still in transit."""
        connection_label = self.drones.get_connection_label(drone_id)

        if connection_label is None:
            raise RuntimeError("Transit drone has no connection label.")

        movements.append(f"D{drone_id}-{connection_label}")
        processed_drones.add(drone_id)

    def _apply_transit_arrivals(
        self,
        arrivals: list[TransitArrival],
        movements: list[str],
        zone_occupancy: dict[str, int],
        processed_drones: set[int],
    ) -> None:
        """Place completed transit drones into their target zones."""
        for drone_id, target_zone in arrivals:
            previous_zone = self.drones.get_zone(drone_id)

            self.drones.finish_transit(drone_id, target_zone)

            if previous_zone != target_zone:
                movements.append(f"D{drone_id}-{target_zone}")

            processed_drones.add(drone_id)

            if target_zone == self.end_zone:
                self.drones.mark_delivered(drone_id)

    def _collect_move_intents(
        self,
        processed_drones: set[int],
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
    ) -> list[MoveIntent]:
        """Collect movement intents for drones that can act this turn."""
        intents: list[MoveIntent] = []

        for drone_id in iter_drone_ids(self.nb_drones):
            if self._should_skip_drone_for_intent(
                drone_id,
                processed_drones,
            ):
                continue

            current_zone = self.drones.get_zone(drone_id)

            if current_zone is None:
                continue

            if current_zone == self.end_zone:
                self.drones.mark_delivered(drone_id)
                processed_drones.add(drone_id)
                continue

            intent = self._build_move_intent(
                drone_id,
                current_zone,
                zone_occupancy,
                link_usage,
            )

            if intent is not None:
                intents.append(intent)

        return intents

    def _should_skip_drone_for_intent(
        self,
        drone_id: int,
        processed_drones: set[int],
    ) -> bool:
        """Return whether a drone should not create a move intent."""
        if self.drones.is_delivered(drone_id):
            return True

        if drone_id in processed_drones:
            return True

        return self.drones.is_in_transit(drone_id)

    def _build_move_intent(
        self,
        drone_id: int,
        current_zone: str,
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
    ) -> MoveIntent | None:
        """Build a movement intent for one drone when possible."""
        next_zone = self.routes.choose_next_zone(
            drone_id,
            current_zone,
            zone_occupancy,
            link_usage,
        )

        if next_zone is None:
            return None

        if next_zone == current_zone:
            return None

        if self.graph.is_blocked(next_zone):
            return None

        connection = self.graph.get_connection(current_zone, next_zone)

        if connection is None:
            return None

        return MoveIntent(
            drone_id=drone_id,
            from_zone=current_zone,
            to_zone=next_zone,
            connection=connection,
            is_restricted=self.graph.is_restricted(next_zone),
            zone_type=self.graph.get_zone(next_zone).zone_type,
            remaining_cost=self.routes.estimate_remaining_cost(next_zone),
            wait_turns=self.drones.get_wait_turns(drone_id),
        )

    def _apply_move_intents(
        self,
        approved_intents: list[MoveIntent],
        movements: list[str],
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
        processed_drones: set[int],
    ) -> None:
        """Apply approved movement intents to the simulation state."""
        for intent in approved_intents:
            if intent.from_zone == intent.to_zone:
                processed_drones.add(intent.drone_id)
                continue

            connection_key = make_connection_key(
                intent.connection.zone_a,
                intent.connection.zone_b,
            )

            adjust_count(link_usage, connection_key)

            if intent.from_zone != self.start_zone:
                adjust_count(zone_occupancy, intent.from_zone, -1)

            if intent.is_restricted:
                self._start_restricted_transit(
                    intent,
                    connection_key,
                    movements,
                    zone_occupancy,
                    processed_drones,
                )
                continue

            self._move_directly(
                intent,
                movements,
                zone_occupancy,
                processed_drones,
            )

    def _start_restricted_transit(
        self,
        intent: MoveIntent,
        connection_key: frozenset[str],
        movements: list[str],
        zone_occupancy: dict[str, int],
        processed_drones: set[int],
    ) -> None:
        """Start a multi-turn movement into a restricted zone."""
        remaining_turns = self.graph.get_movement_cost(intent.to_zone) - 1

        self.drones.start_transit(
            drone_id=intent.drone_id,
            target_zone=intent.to_zone,
            remaining_turns=remaining_turns,
            connection_label=f"{intent.from_zone}-{intent.to_zone}",
            connection_key=connection_key,
        )

        adjust_count(zone_occupancy, intent.to_zone)

        movements.append(
            f"D{intent.drone_id}-{intent.from_zone}-{intent.to_zone}"
        )
        processed_drones.add(intent.drone_id)

    def _move_directly(
        self,
        intent: MoveIntent,
        movements: list[str],
        zone_occupancy: dict[str, int],
        processed_drones: set[int],
    ) -> None:
        """Move a drone directly into the next zone."""
        self.drones.move_to_zone(intent.drone_id, intent.to_zone)

        adjust_count(zone_occupancy, intent.to_zone)

        movements.append(f"D{intent.drone_id}-{intent.to_zone}")
        processed_drones.add(intent.drone_id)

        if intent.to_zone == self.end_zone:
            self.drones.mark_delivered(intent.drone_id)

    def _update_wait_counters(self, processed_drones: set[int]) -> None:
        """Increase wait counters for drones that did not move this turn."""
        for drone_id in iter_drone_ids(self.nb_drones):
            if self.drones.is_delivered(drone_id):
                continue

            if drone_id in processed_drones:
                continue

            if self.drones.is_in_transit(drone_id):
                continue

            self.drones.increase_wait_turns(drone_id)
