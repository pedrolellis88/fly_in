"""Define graph data models used by the Fly-in simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.Utils.adjacency import build_bidirectional_adjacency
from src.Utils.connection_key import make_connection_key


@dataclass
class Zone:
    """Represent a map zone with position, capacity, type, and role."""

    name: str
    x: int
    y: int
    zone_type: str = "normal"
    color: str = "none"
    max_drones: int = 1
    role: str = "normal"

    def is_start(self) -> bool:
        """Return whether this zone is the start zone."""
        return self.role == "start"

    def is_end(self) -> bool:
        """Return whether this zone is the end zone."""
        return self.role == "end"


@dataclass
class Connection:
    """Represent a bidirectional link between two zones."""

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    def connects(self, zone_name: str) -> bool:
        """Return whether this connection contains the given zone."""
        return self.zone_a == zone_name or self.zone_b == zone_name

    def get_other_zone(self, zone_name: str) -> str:
        """Return the zone connected to the given zone.

        Raise:
            ValueError: If the given zone does not belong to this connection.
        """
        if zone_name == self.zone_a:
            return self.zone_b
        if zone_name == self.zone_b:
            return self.zone_a
        raise ValueError(f"Zone '{zone_name}' is not part of this connection.")


@dataclass
class Graph:
    """Represent the full Fly-in map as an adjacency-list graph."""

    nb_drones: int
    start: str
    end: str
    zones: dict[str, Zone] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    adjacency: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_parsed_data(cls, data: dict[str, Any]) -> "Graph":
        """Build a graph from validated parser data."""
        zones: dict[str, Zone] = {}

        zone_name: str
        zone_data: dict[str, Any]
        for zone_name, zone_data in data["zones"].items():
            zones[zone_name] = Zone(
                name=zone_data["name"],
                x=zone_data["x"],
                y=zone_data["y"],
                zone_type=zone_data["zone_type"],
                color=zone_data["color"],
                max_drones=zone_data["max_drones"],
                role=zone_data["role"],
            )

        connections: list[Connection] = []
        connection_data: dict[str, Any]
        for connection_data in data["connections"]:
            connections.append(
                Connection(
                    zone_a=connection_data["from"],
                    zone_b=connection_data["to"],
                    max_link_capacity=connection_data["max_link_capacity"],
                )
            )

        graph = cls(
            nb_drones=data["nb_drones"],
            start=data["start"],
            end=data["end"],
            zones=zones,
            connections=connections,
        )
        graph._build_adjacency()
        return graph

    def _build_adjacency(self) -> None:
        """Build the adjacency list from all graph connections."""
        self.adjacency = build_bidirectional_adjacency(
            self.zones,
            (
                (connection.zone_a, connection.zone_b)
                for connection in self.connections
            ),
        )

    def get_zone(self, zone_name: str) -> Zone:
        """Return the zone matching the given name.

        Raise:
            ValueError: If the zone does not exist in the graph.
        """
        if zone_name not in self.zones:
            raise ValueError(f"Unknown zone '{zone_name}'.")
        return self.zones[zone_name]

    def get_neighbors(self, zone_name: str) -> list[str]:
        """Return all zones directly connected to the given zone.

        Raise:
            ValueError: If the zone does not exist in the adjacency list.
        """
        if zone_name not in self.adjacency:
            raise ValueError(f"Unknown zone '{zone_name}'.")
        return self.adjacency[zone_name]

    def get_connection(self, zone_a: str, zone_b: str) -> Connection | None:
        """Return the connection between two zones, if one exists."""
        requested_key = make_connection_key(zone_a, zone_b)

        connection: Connection
        for connection in self.connections:
            connection_key = make_connection_key(
                connection.zone_a,
                connection.zone_b,
            )
            if connection_key == requested_key:
                return connection
        return None

    def is_blocked(self, zone_name: str) -> bool:
        """Return whether the given zone is blocked."""
        return self.get_zone(zone_name).zone_type == "blocked"

    def is_priority(self, zone_name: str) -> bool:
        """Return whether the given zone is a priority zone."""
        return self.get_zone(zone_name).zone_type == "priority"

    def is_restricted(self, zone_name: str) -> bool:
        """Return whether the given zone is restricted."""
        return self.get_zone(zone_name).zone_type == "restricted"

    def get_zone_capacity(self, zone_name: str) -> int:
        """Return the maximum number of drones allowed in a zone.

        Start and end zones can contain all drones.
        """
        zone = self.get_zone(zone_name)

        if zone.is_start() or zone.is_end():
            return self.nb_drones

        return zone.max_drones

    def get_movement_cost(self, zone_name: str) -> int:
        """Return the movement cost required to enter a zone."""
        zone = self.get_zone(zone_name)

        if zone.zone_type == "restricted":
            return 2

        return 1
