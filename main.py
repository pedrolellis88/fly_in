"""Entry point for the Fly-in project."""

from __future__ import annotations

import sys
from pathlib import Path

from src.parser.map_parser import MapParser, MapParserError


def main() -> int:
    """Run the Fly-in program."""
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>")
        return 1

    map_path = Path(sys.argv[1])

    if not map_path.is_file():
        print(f"Error: map file not found: {map_path}")
        return 1

    try:
        parser = MapParser()
        parsed_map = parser.parse(map_path)

        print(f"Map loaded successfully: {map_path}")
        print(f"Drones: {parsed_map['nb_drones']}")
        print(f"Start: {parsed_map['start']}")
        print(f"End: {parsed_map['end']}")
        print(f"Zones: {len(parsed_map['zones'])}")
        print(f"Connections: {len(parsed_map['connections'])}")
        return 0
    except MapParserError as error:
        print(f"Parse error: {error}")
        return 1
    except Exception as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
