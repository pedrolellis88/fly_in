"""Parser for Fly-in map files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .declaration_parser import ConnectionParser
from .declaration_parser import MapParserError as MapParserError
from .declaration_parser import MetadataParser
from .declaration_parser import NumberParser
from .declaration_parser import ZoneParser
from .map_validator import MapValidator


class MapParser:
    """Coordinate parsing and validation of Fly-in map files."""

    def __init__(self) -> None:
        metadata_parser = MetadataParser()

        self._zone_parser = ZoneParser(metadata_parser)
        self._connection_parser = ConnectionParser(metadata_parser)
        self._validator = MapValidator()

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """Read, parse, and validate a Fly-in map file."""
        lines = self._read_lines(file_path)

        if not lines:
            raise MapParserError("Empty map file.")

        data = self._create_initial_data()
        conn_keys: set[frozenset[str]] = set()

        for index, raw_line in enumerate(lines, start=1):
            line = self._clean_line(raw_line)
            if line:
                self._parse_line(line, index, data, conn_keys)

        self._validator.validate(data)
        return data

    def _read_lines(self, file_path: str | Path) -> list[str]:
        """Read map file lines."""
        path = Path(file_path)

        try:
            return path.read_text(encoding="utf-8-sig").splitlines()
        except FileNotFoundError as exc:
            raise MapParserError(f"Map file not found: {path}") from exc
        except OSError as exc:
            raise MapParserError(f"Could not read map file: {path}") from exc

    def _create_initial_data(self) -> dict[str, Any]:
        """Create the initial parsed map structure."""
        return {
            "nb_drones": None,
            "start": None,
            "end": None,
            "zones": {},
            "connections": [],
        }

    def _clean_line(self, raw_line: str) -> str:
        """Remove comments and surrounding whitespace from a line."""
        return raw_line.split("#", maxsplit=1)[0].strip()

    def _parse_line(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
        conn_keys: set[frozenset[str]],
    ) -> None:
        """Dispatch one non-empty line to the correct parser."""
        if data["nb_drones"] is None and not line.startswith("nb_drones:"):
            raise MapParserError(
                f"Line {line_number}: nb_drones must be the first valid line."
            )

        if line.startswith("nb_drones:"):
            self._parse_nb_drones(line, line_number, data)
        elif line.startswith("start_hub:"):
            self._zone_parser.parse(line, line_number, "start_hub", data)
        elif line.startswith("end_hub:"):
            self._zone_parser.parse(line, line_number, "end_hub", data)
        elif line.startswith("hub:"):
            self._zone_parser.parse(line, line_number, "hub", data)
        elif line.startswith("connection:"):
            self._connection_parser.parse(
                line,
                line_number,
                data,
                conn_keys,
            )
        else:
            raise MapParserError(
                f"Line {line_number}: unknown instruction: {line!r}"
            )

    def _parse_nb_drones(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
    ) -> None:
        """Parse the nb_drones declaration."""
        if data["nb_drones"] is not None:
            raise MapParserError(
                f"Line {line_number}: nb_drones already defined."
            )

        value = line.partition(":")[2].strip()
        if not value:
            raise MapParserError(
                f"Line {line_number}: nb_drones requires a value."
            )

        data["nb_drones"] = NumberParser.parse_positive_int(
            value,
            line_number,
            "nb_drones",
        )
