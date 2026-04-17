"""Parser for Fly-in map files."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any


class MapParserError(Exception):
    """Raised when the map file contains invalid syntax or invalid data."""


class MapParser:
    """Parse Fly-in map files into a validated dictionary structure."""

    VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """Parse a map file and return its validated configuration."""
        path = Path(file_path)
        lines = self._read_lines(path)

        if not lines:
            raise MapParserError("Empty map file.")

        data: dict[str, Any] = {
            "nb_drones": 0,
            "start": None,
            "end": None,
            "zones": {},
            "connections": [],
        }

        connection_keys: set[frozenset[str]] = set()

        for index, raw_line in enumerate(lines, start=1):
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue
            self._parse_line(line, index, data, connection_keys)

        self._validate_final_structure(data)

        return data

    def _read_lines(self, path: Path) -> list[str]:
        """Read all lines from a map file."""
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError as exc:
            raise MapParserError(f"Map file not found: {path}") from exc
        except OSError as exc:
            raise MapParserError(f"Could not read map file: {path}") from exc

    def _strip_comment(self, line: str) -> str:
        """Remove comment part from a line."""
        return line.split("#", maxsplit=1)[0]

    def _parse_line(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
        connection_keys: set[frozenset[str]],
    ) -> None:
        """Dispatch line parsing according to its prefix."""
        if line.startswith("nb_drones:"):
            self._parse_nb_drones(line, line_number, data)
        elif line.startswith("start_hub:"):
            self._parse_zone(line, line_number, data, "start_hub")
        elif line.startswith("end_hub:"):
            self._parse_zone(line, line_number, data, "end_hub")
        elif line.startswith("hub:"):
            self._parse_zone(line, line_number, data, "hub")
        elif line.startswith("connection:"):
            self._parse_connection(line, line_number, data, connection_keys)
        else:
            raise MapParserError(
                f"Line {line_number}: unknown instruction: {line}"
            )

    def _parse_nb_drones(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
    ) -> None:
        """Parse the number of drones."""
        if data["nb_drones"] != 0:
            raise MapParserError(
                f"Line {line_number}: nb_drones already defined."
            )

        match = re.fullmatch(r"nb_drones:\s*(\d+)", line)
        if match is None:
            raise MapParserError(
                f"Line {line_number}: invalid nb_drones syntax."
            )

        nb_drones = int(match.group(1))
        if nb_drones <= 0:
            raise MapParserError(
                f"Line {line_number}: nb_drones must be a positive integer."
            )

        data["nb_drones"] = nb_drones

    def _parse_zone(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
        prefix: str,
    ) -> None:
        """Parse a zone definition."""
        pattern = (
            r"(start_hub|end_hub|hub):\s+([^\s-]+)\s+(-?\d+)\s+(-?\d+)"
            r"(?:\s*(\[[^\]]+\]))?$"
        )
        match = re.fullmatch(pattern, line)
        if match is None:
            raise MapParserError(
                f"Line {line_number}: invalid zone syntax."
            )

        zone_name = match.group(2)
        x_coord = int(match.group(3))
        y_coord = int(match.group(4))
        metadata_raw = match.group(5)

        if zone_name in data["zones"]:
            raise MapParserError(
                f"Line {line_number}: duplicate zone name '{zone_name}'."
            )

        metadata = self._parse_zone_metadata(metadata_raw, line_number)

        zone_data = {
            "name": zone_name,
            "x": x_coord,
            "y": y_coord,
            "zone_type": metadata["zone"],
            "color": metadata["color"],
            "max_drones": metadata["max_drones"],
            "role": self._prefix_to_role(prefix),
        }

        data["zones"][zone_name] = zone_data

        if prefix == "start_hub":
            if data["start"] is not None:
                raise MapParserError(
                    f"Line {line_number}: multiple start_hub definitions."
                )
            data["start"] = zone_name
        elif prefix == "end_hub":
            if data["end"] is not None:
                raise MapParserError(
                    f"Line {line_number}: multiple end_hub definitions."
                )
            data["end"] = zone_name

    def _parse_connection(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
        connection_keys: set[frozenset[str]],
    ) -> None:
        """Parse a connection definition."""
        pattern = (
            r"connection:\s+([^\s-]+)-([^\s-]+)"
            r"(?:\s*(\[[^\]]+\]))?$"
        )
        match = re.fullmatch(pattern, line)
        if match is None:
            raise MapParserError(
                f"Line {line_number}: invalid connection syntax."
            )

        zone_a = match.group(1)
        zone_b = match.group(2)
        metadata_raw = match.group(3)

        if zone_a == zone_b:
            raise MapParserError(
                f"Line {line_number}: self-connections are not allowed."
            )

        if zone_a not in data["zones"] or zone_b not in data["zones"]:
            raise MapParserError(
                f"Line {line_number}: connection uses undefined zone."
            )

        key = frozenset({zone_a, zone_b})
        if key in connection_keys:
            raise MapParserError(
                f"Line {line_number}: double connection '{zone_a}-{zone_b}'."
            )

        metadata = self._parse_connection_metadata(metadata_raw, line_number)

        data["connections"].append(
            {
                "from": zone_a,
                "to": zone_b,
                "max_link_capacity": metadata["max_link_capacity"],
            }
        )
        connection_keys.add(key)

    def _parse_zone_metadata(
        self,
        metadata_raw: str | None,
        line_number: int,
    ) -> dict[str, Any]:
        """Parse metadata for a zone."""
        metadata: dict[str, Any] = {
            "zone": "normal",
            "color": "none",
            "max_drones": 1,
        }

        if metadata_raw is None:
            return metadata

        pairs = self._parse_metadata_block(metadata_raw, line_number)

        for key, value in pairs.items():
            if key == "zone":
                if value not in self.VALID_ZONE_TYPES:
                    raise MapParserError(
                        f"Line {line_number}: invalid zone type '{value}'."
                    )
                metadata["zone"] = value
            elif key == "color":
                metadata["color"] = value
            elif key == "max_drones":
                capacity = self._parse_positive_int(
                    value,
                    line_number,
                    "max_drones",
                )
                metadata["max_drones"] = capacity
            else:
                raise MapParserError(
                    f"Line {line_number}: invalid zone metadata key '{key}'."
                )

        return metadata

    def _parse_connection_metadata(
        self,
        metadata_raw: str | None,
        line_number: int,
    ) -> dict[str, Any]:
        """Parse metadata for a connection."""
        metadata = {"max_link_capacity": 1}

        if metadata_raw is None:
            return metadata

        pairs = self._parse_metadata_block(metadata_raw, line_number)

        for key, value in pairs.items():
            if key != "max_link_capacity":
                raise MapParserError(
                    f"Line {line_number}: invalid connection metadata key "
                    f"'{key}'."
                )
            metadata["max_link_capacity"] = self._parse_positive_int(
                value,
                line_number,
                "max_link_capacity",
            )

        return metadata

    def _parse_metadata_block(
        self,
        metadata_raw: str,
        line_number: int,
    ) -> dict[str, str]:
        """Parse a [key=value ...] metadata block."""
        if not metadata_raw.startswith("[") or not metadata_raw.endswith("]"):
            raise MapParserError(
                f"Line {line_number}: invalid metadata block."
            )

        content = metadata_raw[1:-1].strip()
        if not content:
            return {}

        parts = content.split()
        pairs: dict[str, str] = {}

        for part in parts:
            if "=" not in part:
                raise MapParserError(
                    f"Line {line_number}: invalid metadata entry '{part}'."
                )
            key, value = part.split("=", maxsplit=1)
            if not key or not value:
                raise MapParserError(
                    f"Line {line_number}: invalid metadata entry '{part}'."
                )
            if key in pairs:
                raise MapParserError(
                    f"Line {line_number}: duplicate metadata key '{key}'."
                )
            pairs[key] = value

        return pairs

    def _parse_positive_int(
        self,
        value: str,
        line_number: int,
        field_name: str,
    ) -> int:
        """Parse a positive integer metadata value."""
        if not value.isdigit():
            raise MapParserError(
                f"Line {line_number}: {field_name} must be a positive integer."
            )

        parsed_value = int(value)
        if parsed_value <= 0:
            raise MapParserError(
                f"Line {line_number}: {field_name} must be a positive integer."
            )

        return parsed_value

    def _prefix_to_role(self, prefix: str) -> str:
        """Convert line prefix to internal role name."""
        if prefix == "start_hub":
            return "start"
        if prefix == "end_hub":
            return "end"
        return "normal"

    def _validate_final_structure(self, data: dict[str, Any]) -> None:
        """Validate mandatory map requirements after parsing."""
        if data["nb_drones"] == 0:
            raise MapParserError("Missing nb_drones definition.")
        if data["start"] is None:
            raise MapParserError("Missing start_hub definition.")
        if data["end"] is None:
            raise MapParserError("Missing end_hub definition.")
        if not data["connections"]:
            raise MapParserError("Map must contain at least one connection.")
