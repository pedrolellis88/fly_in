"""Run the Fly-in application from the command line."""

from __future__ import annotations

import sys
from pathlib import Path

from src.Models.graph import Graph
from src.Parser.map_parser import MapParser, MapParserError
from src.Pathfinding.dijkstra import PathNotFoundError
from src.Simulation.simulator import Simulator
from src.Visualization.graphical_renderer import GraphicalRenderer


def build_simulator(map_path: Path) -> Simulator:
    """Create a simulator from a parsed map file."""
    parser = MapParser()
    parsed_map = parser.parse(map_path)
    graph = Graph.from_parsed_data(parsed_map)
    return Simulator(graph)


def main() -> int:
    """Validate arguments, build the simulator, and run the GUI."""
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>")
        return 1

    map_path = Path(sys.argv[1])

    if not map_path.is_file():
        print(f"Error: map file not found: {map_path}")
        return 1

    try:
        simulator = build_simulator(map_path)
        renderer = GraphicalRenderer(
            simulator.graph,
            map_path,
            build_simulator,
        )
        renderer.attach_simulator(simulator)
        renderer.run()
        return 0

    except MapParserError as error:
        print(f"Parse error: {error}")
        return 1
    except PathNotFoundError as error:
        print(f"Pathfinding error: {error}")
        return 1
    except Exception as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
