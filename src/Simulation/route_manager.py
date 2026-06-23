"""Manage route choice logic for the Fly-in simulation."""

from __future__ import annotations

from collections import Counter
from typing import Callable

from src.Models.graph import Connection, Graph
from src.Pathfinding.dijkstra import Dijkstra
from src.Simulation.drone_manager import DroneManager
from src.Utils.connection_key import make_connection_key
from src.Utils.drone_ids import iter_drone_ids
from src.Utils.paths import get_next_path_item, get_path_suffix

Pathfinder = Callable[[Graph], list[list[str]]]


class _RouteCostCalculator:
    """Calculate route costs using graph movement costs."""

    UNREACHABLE_COST = 9999.0

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def movement_cost_for_zone(self, zone_name: str) -> int:
        """Return the effective movement cost for entering a zone."""
        return max(self.graph.get_movement_cost(zone_name), 1)

    def path_cost(self, path: list[str]) -> float:
        """Return the total cost of a complete path."""
        return self.suffix_cost(path)

    def suffix_cost(self, path_suffix: list[str]) -> float:
        """Return the cost of moving through a path suffix."""
        return float(sum(
            self.movement_cost_for_zone(zone_name)
            for zone_name in path_suffix[1:]
        ))

    def estimate_remaining_cost(
        self,
        zone_name: str,
        available_paths: list[list[str]],
    ) -> float:
        """Return the lowest known cost from a zone to the end."""
        costs: list[float] = []

        for path in available_paths:
            suffix = get_path_suffix(path, zone_name)
            if suffix is None or path[-1] != self.graph.end:
                continue

            costs.append(self.suffix_cost(suffix))

        return min(costs, default=self.UNREACHABLE_COST)

    def move_total_cost(
        self,
        next_zone: str,
        available_paths: list[list[str]],
    ) -> float:
        """Return the move cost plus the cheapest known continuation."""
        return (
            self.movement_cost_for_zone(next_zone)
            + self.estimate_remaining_cost(next_zone, available_paths)
        )


class _PathRepository:
    """Prepare, assign, and query paths available to drones."""

    ASSIGNMENT_LOAD_FACTOR = 0.25
    SHARED_ZONE_PENALTY = 0.55
    UNAVOIDABLE_ZONE_RATIO = 0.95

    def __init__(
        self,
        graph: Graph,
        paths: list[list[str]],
        cost_calculator: _RouteCostCalculator,
    ) -> None:
        self.graph = graph
        self.cost_calculator = cost_calculator
        self.available_paths = self._prepare_available_paths(paths)
        self.unavoidable_zones = self._find_unavoidable_zones()
        self.assigned_zone_loads: Counter[str] = Counter()

    def _prepare_available_paths(
        self,
        paths: list[list[str]],
    ) -> list[list[str]]:
        """Clean, deduplicate, and sort paths before assignment."""
        prepared: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()

        for path in paths:
            key = tuple(path)
            if not self._is_valid_complete_path(path) or key in seen:
                continue

            seen.add(key)
            prepared.append(path)

        prepared.sort(key=self.cost_calculator.path_cost)
        return prepared

    def _is_valid_complete_path(self, path: list[str]) -> bool:
        """Return whether a path can be used from start to end."""
        if (
            len(path) < 2
            or path[0] != self.graph.start
            or path[-1] != self.graph.end
            or len(set(path)) != len(path)
        ):
            return False

        return all(
            zone_name in self.graph.zones
            and not self.graph.is_blocked(zone_name)
            for zone_name in path
        )

    def _find_unavoidable_zones(self) -> set[str]:
        """Return zones that appear in almost every available path."""
        if not self.available_paths:
            return set()

        zone_frequency: Counter[str] = Counter()
        for path in self.available_paths:
            zone_frequency.update(set(path[1:-1]))

        threshold = len(self.available_paths) * self.UNAVOIDABLE_ZONE_RATIO
        return {
            zone_name
            for zone_name, frequency in zone_frequency.items()
            if frequency >= threshold
        }

    def choose_best_path_index(self, path_loads: list[int]) -> int:
        """Return the index of the best path for a new drone assignment."""
        best_index = 0
        best_cost: float | None = None

        for index, path in enumerate(self.available_paths):
            cost = self._assignment_cost(path, path_loads[index])
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_index = index

        self._register_assigned_path(self.available_paths[best_index])
        return best_index

    def _assignment_cost(self, path: list[str], current_load: int) -> float:
        """Return path assignment cost including existing route pressure."""
        return (
            self.cost_calculator.path_cost(path)
            + current_load * self.ASSIGNMENT_LOAD_FACTOR
            + self._shared_zone_assignment_cost(path)
        )

    def _shared_zone_assignment_cost(self, path: list[str]) -> float:
        """Return extra cost for reusing avoidable capacity-one zones."""
        return sum(
            self.assigned_zone_loads[zone_name] * self.SHARED_ZONE_PENALTY
            for zone_name in path[1:-1]
            if self._should_count_shared_zone(zone_name)
        )

    def _register_assigned_path(self, path: list[str]) -> None:
        """Update shared-zone loads after assigning a path."""
        for zone_name in path[1:-1]:
            if self._should_count_shared_zone(zone_name):
                self.assigned_zone_loads[zone_name] += 1

    def _should_count_shared_zone(self, zone_name: str) -> bool:
        """Return whether a zone should affect initial path distribution."""
        return (
            zone_name not in self.unavoidable_zones
            and self.graph.get_zone(zone_name).max_drones == 1
        )

    def get_candidate_next_zones(
        self,
        current_path: list[str] | None,
        current_zone: str,
    ) -> list[str]:
        """Return possible next zones from the current position."""
        candidates: list[str] = []
        seen: set[str] = set()

        if current_path is not None:
            next_zone = get_next_path_item(current_path, current_zone)
            if next_zone is not None:
                seen.add(next_zone)
                candidates.append(next_zone)

        for path in self.available_paths:
            next_zone = get_next_path_item(path, current_zone)
            if next_zone is None:
                continue

            if next_zone not in seen:
                seen.add(next_zone)
                candidates.append(next_zone)

        return candidates

    def estimate_remaining_cost(self, zone_name: str) -> float:
        """Return the lowest known cost from a zone to the end."""
        return self.cost_calculator.estimate_remaining_cost(
            zone_name,
            self.available_paths,
        )

    def move_total_cost(self, next_zone: str) -> float:
        """Return movement cost plus remaining route cost."""
        return self.cost_calculator.move_total_cost(
            next_zone,
            self.available_paths,
        )

    def find_best_suffix(
        self,
        current_zone: str,
        chosen_next_zone: str,
    ) -> list[str] | None:
        """Return the cheapest suffix matching a chosen next zone."""
        best_suffix: list[str] | None = None
        best_cost: float | None = None

        for path in self.available_paths:
            suffix = get_path_suffix(path, current_zone)
            if suffix is None or len(suffix) < 2:
                continue

            if suffix[1] != chosen_next_zone:
                continue

            cost = self.cost_calculator.suffix_cost(suffix)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_suffix = suffix

        return best_suffix


class _RouteMemory:
    """Remember recently visited zones to reduce routing loops."""

    RECENT_ZONE_MEMORY = 4

    def __init__(
        self,
        nb_drones: int,
        start_zone: str,
        end_zone: str,
    ) -> None:
        self.end_zone = end_zone
        self.recent_zones: dict[int, list[str]] = {
            drone_id: [start_zone]
            for drone_id in iter_drone_ids(nb_drones)
        }

    def remember_current_zone(self, drone_id: int, zone_name: str) -> None:
        """Store a short recent-zone history for a drone."""
        recent = self.recent_zones.setdefault(drone_id, [])
        if recent and recent[-1] == zone_name:
            return

        recent.append(zone_name)
        if len(recent) > self.RECENT_ZONE_MEMORY:
            del recent[0: len(recent) - self.RECENT_ZONE_MEMORY]

    def remove_loop_candidates(
        self,
        drone_id: int,
        current_zone: str,
        candidates: list[str],
    ) -> list[str]:
        """Remove recently visited candidates when alternatives exist."""
        safe_candidates = [
            candidate
            for candidate in candidates
            if not self.is_recent_revisit(drone_id, candidate)
        ]
        if safe_candidates:
            return safe_candidates

        return [
            candidate
            for candidate in candidates
            if not self.is_immediate_backtrack(
                drone_id,
                current_zone,
                candidate,
            )
        ]

    def is_recent_revisit(self, drone_id: int, zone_name: str) -> bool:
        """Return whether the zone was recently visited by this drone."""
        if zone_name == self.end_zone:
            return False

        recent = self.recent_zones.get(drone_id, [])
        return zone_name in recent[-self.RECENT_ZONE_MEMORY:]

    def is_immediate_backtrack(
        self,
        drone_id: int,
        current_zone: str,
        candidate_zone: str,
    ) -> bool:
        """Return whether the candidate immediately reverses the last move."""
        recent = self.recent_zones.get(drone_id, [])
        if len(recent) < 2:
            return False

        return (
            recent[-1] == current_zone
            and candidate_zone == recent[-2]
        )


class RouteManager:
    """Assign paths and choose dynamic next moves for drones."""

    RECENT_REVISIT_PENALTY = 900.0
    IMMEDIATE_BACKTRACK_PENALTY = 3000.0

    def __init__(
        self,
        graph: Graph,
        drones: DroneManager,
        pathfinder: Pathfinder | None = None,
    ) -> None:
        """Initialize routes using a custom or default pathfinder."""
        self.graph = graph
        self.drones = drones
        self.pathfinder = pathfinder or self._default_pathfinder

        self.cost_calculator = _RouteCostCalculator(self.graph)
        self.paths = _PathRepository(
            graph=self.graph,
            paths=self.pathfinder(self.graph),
            cost_calculator=self.cost_calculator,
        )
        self.memory = _RouteMemory(
            nb_drones=self.graph.nb_drones,
            start_zone=self.graph.start,
            end_zone=self.graph.end,
        )

        self.available_paths = self.paths.available_paths
        self.drone_paths = self._assign_paths_to_drones()

    def _default_pathfinder(self, graph: Graph) -> list[list[str]]:
        """Return available paths using the default Dijkstra pathfinder."""
        return Dijkstra(graph).find_paths(max_paths=35)

    def _assign_paths_to_drones(self) -> dict[int, list[str]]:
        """Assign an initial path to each drone."""
        if not self.available_paths:
            raise ValueError("No valid paths available.")

        drone_paths: dict[int, list[str]] = {}
        path_loads = [0 for _ in self.available_paths]

        for drone_id in iter_drone_ids(self.graph.nb_drones):
            best_index = self.paths.choose_best_path_index(path_loads)
            selected_path = self.available_paths[best_index]

            drone_paths[drone_id] = selected_path
            self.drones.set_current_path(drone_id, selected_path)
            path_loads[best_index] += 1

        return drone_paths

    def choose_next_zone(
        self,
        drone_id: int,
        current_zone: str,
        zone_occupancy: dict[str, int],
        link_use: dict[frozenset[str], int],
    ) -> str | None:
        """Choose the best next zone for a drone at the current turn."""
        self.memory.remember_current_zone(drone_id, current_zone)

        candidates = self._get_candidates(drone_id, current_zone)

        if not candidates:
            return None

        viable_candidates = self._filter_viable_candidates(
            current_zone,
            candidates,
            link_use,
        )

        if not viable_candidates:
            return None

        non_loop_candidates = self.memory.remove_loop_candidates(
            drone_id,
            current_zone,
            viable_candidates,
        )

        if non_loop_candidates:
            viable_candidates = non_loop_candidates

        best_zone = self._choose_lowest_cost_candidate(
            drone_id,
            current_zone,
            viable_candidates,
            zone_occupancy,
            link_use,
        )

        if best_zone is None:
            return None

        self.memory.remember_current_zone(drone_id, best_zone)
        self._update_drone_path_after_choice(
            drone_id,
            current_zone,
            best_zone,
        )

        return best_zone

    def _get_candidates(
        self,
        drone_id: int,
        current_zone: str,
    ) -> list[str]:
        """Return candidate next zones for a drone."""
        current_path = self.drones.get_current_path(drone_id)

        return self.paths.get_candidate_next_zones(
            current_path=current_path,
            current_zone=current_zone,
        )

    def _filter_viable_candidates(
        self,
        current_zone: str,
        candidates: list[str],
        link_use: dict[frozenset[str], int],
    ) -> list[str]:
        """Return candidates that are not blocked by link rules."""
        viable: list[str] = []

        for candidate_zone in candidates:
            if self._is_candidate_available_now(
                current_zone,
                candidate_zone,
                link_use,
            ):
                viable.append(candidate_zone)

        return viable

    def _is_candidate_available_now(
        self,
        current_zone: str,
        candidate_zone: str,
        link_use: dict[frozenset[str], int],
    ) -> bool:
        """Return whether a candidate is not blocked by connection rules."""
        if self.graph.is_blocked(candidate_zone):
            return False

        connection = self.graph.get_connection(current_zone, candidate_zone)

        if connection is None:
            return False

        connection_key = make_connection_key(
            connection.zone_a,
            connection.zone_b,
        )

        if link_use.get(connection_key, 0) >= connection.max_link_capacity:
            return False

        return True

    def _choose_lowest_cost_candidate(
        self,
        drone_id: int,
        current_zone: str,
        candidates: list[str],
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
    ) -> str | None:
        """Return the candidate with the lowest selection cost."""
        best_zone: str | None = None
        best_cost: float | None = None

        for candidate_zone in candidates:
            connection = self.graph.get_connection(
                current_zone,
                candidate_zone,
            )

            if connection is None:
                continue

            cost = self._candidate_selection_cost(
                drone_id,
                current_zone,
                candidate_zone,
                connection,
                zone_occupancy,
                link_usage,
            )

            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_zone = candidate_zone

        return best_zone

    def _candidate_selection_cost(
        self,
        drone_id: int,
        current_zone: str,
        next_zone: str,
        connection: Connection,
        zone_occupancy: dict[str, int],
        link_usage: dict[frozenset[str], int],
    ) -> float:
        """Return the selection cost for a candidate next zone."""
        cost = self.paths.move_total_cost(next_zone)

        cost += self._capacity_pressure_cost(next_zone, zone_occupancy)
        cost += self._link_pressure_cost(connection, link_usage)
        cost += self._path_change_cost(drone_id, current_zone, next_zone)
        cost += self._loop_cost(drone_id, current_zone, next_zone)

        return cost

    def _capacity_pressure_cost(
        self,
        next_zone: str,
        zone_occupancy: dict[str, int],
    ) -> float:
        """Return extra cost for zones close to capacity."""
        if self.graph.is_restricted(next_zone):
            return 0.0

        target_capacity = self.graph.get_zone_capacity(next_zone)
        target_occupancy = zone_occupancy.get(next_zone, 0)

        if target_capacity <= 0:
            return 0.0

        occupancy_ratio = target_occupancy / target_capacity
        cost = occupancy_ratio * 20.0

        if target_occupancy >= target_capacity:
            cost += 80.0

        return cost

    def _link_pressure_cost(
        self,
        connection: Connection,
        link_usage: dict[frozenset[str], int],
    ) -> float:
        """Return extra cost for busy connections."""
        if connection.max_link_capacity <= 0:
            return 0.0

        connection_key = make_connection_key(
            connection.zone_a,
            connection.zone_b,
        )
        current_link_usage = link_usage.get(connection_key, 0)

        return (current_link_usage / connection.max_link_capacity) * 3.0

    def _path_change_cost(
        self,
        drone_id: int,
        current_zone: str,
        next_zone: str,
    ) -> float:
        """Return a small cost for leaving the assigned path."""
        current_path = self.drones.get_current_path(drone_id)

        if current_path is None:
            return 0.0

        preferred_next = get_next_path_item(current_path, current_zone)
        if preferred_next is None:
            return 0.0

        if next_zone == preferred_next:
            return 0.0

        return 2.0

    def _loop_cost(
        self,
        drone_id: int,
        current_zone: str,
        next_zone: str,
    ) -> float:
        """Return extra cost for movements that may create loops."""
        cost = 0.0

        if self.memory.is_recent_revisit(drone_id, next_zone):
            cost += self.RECENT_REVISIT_PENALTY

        if self.memory.is_immediate_backtrack(
            drone_id,
            current_zone,
            next_zone,
        ):
            cost += self.IMMEDIATE_BACKTRACK_PENALTY

        return cost

    def _update_drone_path_after_choice(
        self,
        drone_id: int,
        current_zone: str,
        chosen_next_zone: str,
    ) -> None:
        """Update a drone path after a dynamic route choice."""
        current_path = self.drones.get_current_path(drone_id)

        if self._can_keep_current_path(
            current_path,
            current_zone,
            chosen_next_zone,
        ):
            self._keep_current_path_suffix(
                drone_id,
                current_path,
                current_zone,
            )
            return

        best_suffix = self.paths.find_best_suffix(
            current_zone,
            chosen_next_zone,
        )

        if best_suffix is None:
            return

        self.drones.set_current_path(drone_id, best_suffix)
        self.drone_paths[drone_id] = best_suffix

    def _can_keep_current_path(
        self,
        current_path: list[str] | None,
        current_zone: str,
        chosen_next_zone: str,
    ) -> bool:
        """Return whether the drone can keep its current path suffix."""
        if current_path is None:
            return False

        if get_next_path_item(current_path, current_zone) != chosen_next_zone:
            return False

        return current_path[-1] == self.graph.end

    def _keep_current_path_suffix(
        self,
        drone_id: int,
        current_path: list[str] | None,
        current_zone: str,
    ) -> None:
        """Update the drone path using the current path suffix."""
        if current_path is None:
            return

        suffix = get_path_suffix(current_path, current_zone)
        if suffix is None:
            return

        self.drones.set_current_path(drone_id, suffix)
        self.drone_paths[drone_id] = suffix

    def estimate_remaining_cost(self, zone_name: str) -> float:
        """Return the lowest estimated cost from a zone to the end."""
        return self.paths.estimate_remaining_cost(zone_name)
