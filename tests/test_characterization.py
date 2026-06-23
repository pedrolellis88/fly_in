"""Lock current Fly-in behavior before structural cleanup."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from main import build_simulator, main
from src.Models import Connection as ExportedConnection
from src.Models import Graph as ExportedGraph
from src.Models import Zone as ExportedZone
from src.Models.graph import Connection, Graph, Zone
from src.Parser import MapParser as ExportedMapParser
from src.Parser import MapParserError as ExportedMapParserError
from src.Parser.map_parser import MapParser, MapParserError
from src.Pathfinding import Dijkstra as ExportedDijkstra
from src.Pathfinding import PathNotFoundError as ExportedPathNotFoundError
from src.Pathfinding.dijkstra import Dijkstra, PathNotFoundError
from src.Simulation import Simulator as ExportedSimulator
from src.Simulation.simulator import Simulator
from src.Utils import iter_drone_ids, make_connection_key
from src.Visualization import GraphicalRenderer as ExportedGraphicalRenderer
from src.Visualization.graph_canvas import GraphCanvas
from src.Visualization.graphical_renderer import GraphicalRenderer
from src.Visualization.graphical_renderer import DEFAULT_COLORS
from src.Visualization.visual_state import VisualStateManager
from tests.conftest import run_until_done, write_map


def test_public_entrypoints_are_importable() -> None:
    """Lock the public classes and functions preserved by the cleanup."""
    assert callable(main)
    assert callable(build_simulator)
    assert MapParser.__name__ == "MapParser"
    assert MapParserError.__name__ == "MapParserError"
    assert Graph.__name__ == "Graph"
    assert Zone.__name__ == "Zone"
    assert Connection.__name__ == "Connection"
    assert Dijkstra.__name__ == "Dijkstra"
    assert PathNotFoundError.__name__ == "PathNotFoundError"
    assert Simulator.__name__ == "Simulator"
    assert GraphicalRenderer.__name__ == "GraphicalRenderer"
    assert ExportedMapParser is MapParser
    assert ExportedMapParserError is MapParserError
    assert ExportedGraph is Graph
    assert ExportedZone is Zone
    assert ExportedConnection is Connection
    assert ExportedDijkstra is Dijkstra
    assert ExportedPathNotFoundError is PathNotFoundError
    assert ExportedSimulator is Simulator
    assert ExportedGraphicalRenderer is GraphicalRenderer
    assert list(iter_drone_ids(2)) == [1, 2]
    assert make_connection_key("a", "b") == frozenset({"a", "b"})


def test_parser_returns_exact_current_structure(tmp_path: Path) -> None:
    """Lock parser defaults, roles, metadata, and source line numbers."""
    path = write_map(
        tmp_path,
        """
        # Characterization map
        nb_drones: 3

        start_hub: start -1 0 [color=green max_drones=3]
        hub: middle 2 -4 [zone=restricted color=orange max_drones=2]
        end_hub: end 6 0 [color=red]

        connection: start-middle [max_link_capacity=2]
        connection: middle-end
        """,
    )

    assert MapParser().parse(path) == {
        "nb_drones": 3,
        "start": "start",
        "end": "end",
        "zones": {
            "start": {
                "name": "start",
                "x": -1,
                "y": 0,
                "zone_type": "normal",
                "color": "green",
                "max_drones": 3,
                "role": "start",
            },
            "middle": {
                "name": "middle",
                "x": 2,
                "y": -4,
                "zone_type": "restricted",
                "color": "orange",
                "max_drones": 2,
                "role": "normal",
            },
            "end": {
                "name": "end",
                "x": 6,
                "y": 0,
                "zone_type": "normal",
                "color": "red",
                "max_drones": 1,
                "role": "end",
            },
        },
        "connections": [
            {
                "from": "start",
                "to": "middle",
                "max_link_capacity": 2,
                "line": 8,
            },
            {
                "from": "middle",
                "to": "end",
                "max_link_capacity": 1,
                "line": 9,
            },
        ],
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            """
            start_hub: start 0 0
            end_hub: end 1 0
            connection: start-end
            """,
            "Line 1: nb_drones must be the first valid line.",
        ),
        (
            """
            nb_drones: 1
            start_hub: start 0 0
            hub: bad 1 0 [zone=banana]
            end_hub: end 2 0
            connection: start-bad
            connection: bad-end
            """,
            "Line 3: invalid zone type 'banana'. Valid types: "
            "['blocked', 'normal', 'priority', 'restricted'].",
        ),
        (
            """
            nb_drones: 1
            start_hub: start 0 0
            end_hub: end 2 0
            connection: start-missing
            """,
            "Line 4: connection references undefined zone 'missing'.",
        ),
        (
            """
            nb_drones: 1
            start_hub: start 0 0
            hub: middle 1 0 [max_drones=0]
            end_hub: end 2 0
            connection: start-middle
            connection: middle-end
            """,
            "Line 3: max_drones must be a positive integer greater than zero, "
            "got '0'.",
        ),
    ],
)
def test_parser_error_messages_are_exact(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Lock representative parser exception text."""
    path = write_map(tmp_path, content)

    with pytest.raises(MapParserError, match=".*") as error:
        MapParser().parse(path)

    assert str(error.value) == message


def test_restricted_simulation_trace_is_exact(tmp_path: Path) -> None:
    """Lock restricted transit timing and movement output order."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: start 0 0
        hub: middle 1 0 [zone=restricted]
        end_hub: end 2 0
        connection: start-middle
        connection: middle-end
        """,
    )

    simulator = build_simulator(path)

    assert run_until_done(simulator) == [
        ["D1-start-middle"],
        ["D2-start-middle", "D1-middle"],
        ["D1-end", "D2-middle"],
        ["D2-end"],
    ]


def test_multi_path_trace_paths_and_assignments_are_exact(
    tmp_path: Path,
) -> None:
    """Lock path order, initial assignment, and conflict resolution."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 3
        start_hub: start 0 0
        hub: a 1 1
        hub: b 1 -1
        hub: merge 2 0
        end_hub: end 3 0
        connection: start-a
        connection: start-b
        connection: a-merge
        connection: b-merge
        connection: merge-end
        """,
    )

    simulator = build_simulator(path)

    assert simulator.get_available_paths() == [
        ["start", "a", "merge", "end"],
        ["start", "b", "merge", "end"],
    ]
    assert simulator.routes.drone_paths == {
        1: ["start", "a", "merge", "end"],
        2: ["start", "b", "merge", "end"],
        3: ["start", "a", "merge", "end"],
    }
    assert run_until_done(simulator) == [
        ["D1-a", "D2-b"],
        ["D1-merge"],
        ["D1-end", "D2-merge", "D3-a"],
        ["D2-end", "D3-merge"],
        ["D3-end"],
    ]


def test_dijkstra_prefers_priority_zone_on_equal_cost_paths(
    tmp_path: Path,
) -> None:
    """Verify priority metadata breaks equal movement-cost path ties."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: start 0 0
        hub: normal_path 1 1
        hub: priority_path 1 -1 [zone=priority]
        end_hub: end 2 0
        connection: start-normal_path
        connection: normal_path-end
        connection: start-priority_path
        connection: priority_path-end
        """,
    )

    simulator = build_simulator(path)

    assert Dijkstra(simulator.graph).find_path() == [
        "start",
        "priority_path",
        "end",
    ]


def test_graph_canvas_uses_explicit_zone_metadata_color() -> None:
    """Verify explicit map colors override role and type defaults."""
    graph = Graph(
        nb_drones=1,
        start="start",
        end="end",
        zones={
            "start": Zone("start", 0, 0, color="purple", role="start"),
            "end": Zone("end", 1, 0, color="cyan", role="end"),
        },
    )
    canvas = GraphCanvas.__new__(GraphCanvas)
    canvas.graph = graph
    canvas.colors = DEFAULT_COLORS.copy()

    assert canvas._zone_color(graph.zones["start"]) == "purple"
    assert canvas._zone_color(graph.zones["end"]) == "cyan"


def test_visual_snapshot_restores_complete_drone_state(tmp_path: Path) -> None:
    """Lock snapshot restoration after removing compatibility properties."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 2
        start_hub: start 0 0
        hub: middle 1 0 [zone=restricted]
        end_hub: end 2 0
        connection: start-middle
        connection: middle-end
        """,
    )
    simulator = build_simulator(path)
    visual_state = VisualStateManager()

    simulator.next_turn()
    simulator.drones.states[1].history.append("checkpoint")
    snapshot = visual_state.capture(simulator)
    expected_states = simulator.drones.capture_states()

    simulator.next_turn()
    simulator.drones.states[1].history.append("mutated")
    visual_state.restore(simulator, snapshot)

    assert simulator.turn == 1
    assert simulator.drones.states == expected_states
    assert simulator.drones.states is not snapshot.drone_states
    assert simulator.drones.states[1] is not snapshot.drone_states[1]


def test_renderer_snapshot_positions_preserve_visual_rules(
    tmp_path: Path,
) -> None:
    """Lock zone, transit, arrival, and delivered visual positions."""
    path = write_map(
        tmp_path,
        """
        nb_drones: 1
        start_hub: start 0 0
        hub: middle 1 0 [zone=restricted]
        end_hub: end 2 0
        connection: start-middle
        connection: middle-end
        """,
    )
    simulator = build_simulator(path)
    renderer = GraphicalRenderer.__new__(GraphicalRenderer)
    renderer.simulator = simulator
    renderer.graph = simulator.graph
    renderer.just_arrived_drones = set()
    renderer.state = VisualStateManager()
    renderer.graph_canvas = cast(
        Any,
        SimpleNamespace(
            layout=SimpleNamespace(
                node_positions={
                    "start": (10.0, 20.0),
                    "middle": (30.0, 20.0),
                    "end": (50.0, 20.0),
                },
            ),
        ),
    )

    assert renderer._snapshot_positions(False) == {1: (10.0, 20.0)}

    simulator.next_turn()
    assert renderer._snapshot_positions(False) == {1: (20.0, 20.0)}

    simulator.next_turn()
    simulator.next_turn()
    renderer.just_arrived_drones = {1}
    assert renderer._snapshot_positions(True) == {1: (50.0, 20.0)}
    assert renderer._snapshot_positions(False) == {1: None}
    assert renderer._snapshot_positions_for_back() == {1: (50.0, 20.0)}


@pytest.mark.parametrize(
    ("map_name", "expected_turns"),
    [
        ("benchmark_linear_6.txt", 11),
        ("benchmark_simple_fork_8.txt", 6),
        ("benchmark_capacity_hell_12.txt", 16),
    ],
)
def test_benchmark_completion_turn_counts_are_exact(
    valid_maps_dir: Path,
    map_name: str,
    expected_turns: int,
) -> None:
    """Lock representative benchmark completion turn counts."""
    simulator = build_simulator(valid_maps_dir / map_name)

    assert len(run_until_done(simulator)) == expected_turns
