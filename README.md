*This project has been created as part of the 42 curriculum by pdiniz-l.*

---

# 🛸 Fly-in

**A drone routing simulator for capacity-constrained zone networks**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00?style=flat-square)
![Pytest](https://img.shields.io/badge/Tests-pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![flake8](https://img.shields.io/badge/Lint-flake8-4B8BBE?style=flat-square)
![mypy](https://img.shields.io/badge/Types-mypy-2A6DB5?style=flat-square)

---

## Description

**Fly-in** is a drone routing simulation project developed in Python. The program receives a map describing a network of connected zones and simulates how multiple drones travel from a **start hub** to an **end hub** while respecting movement and capacity constraints.

The goal is to deliver all drones as efficiently as possible — avoiding blocked zones, handling restricted zones, respecting zone and connection capacities, and distributing drones across multiple available routes.

The project is built entirely from scratch and includes:

- a custom `.txt` map parser with clear error reporting
- a graph model using Python dataclasses
- Dijkstra-based pathfinding with multi-path support
- a turn-based simulation engine with conflict resolution
- capacity and priority management
- a Tkinter graphical interface for step-by-step playback
- automated tests with `pytest`

---

## Instructions

### Requirements

- Python 3.10 or higher
- Tkinter (usually bundled with Python; on Debian/Ubuntu systems run `sudo apt install python3-tk` if missing)

### Installation

Clone the repository and install dependencies:

```bash
make install
```

Or manually:

```bash
pip3 install -r requirements.txt
```

Dependencies: `flake8`, `mypy`, `pytest`

### Running the simulation

Run with the default map:

```bash
make run
```

Run with a specific map file:

```bash
python3 main.py maps/easy/01_linear_path.txt
```

Or using the Makefile `MAP` variable:

```bash
make run MAP=maps/hard/02_capacity_hell.txt
```

Run with the Python debugger:

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

### Tests and code quality

```bash
make test          # run all pytest tests
make lint          # run flake8 + mypy
make lint-strict   # run strict mypy
make clean         # remove cache and temporary files
```

### Map file format

Maps are plain `.txt` files. Every valid map must declare the number of drones, a start hub, an end hub, any number of regular hubs, and connections between them.

```text
nb_drones: 5

start_hub: start 0 0 [color=green]
end_hub: end 10 0 [color=red]

hub: a 2 2 [zone=normal color=blue max_drones=1]
hub: b 4 2 [zone=priority color=yellow max_drones=2]
hub: c 6 2 [zone=restricted color=orange max_drones=1]
hub: d 5 -2 [zone=blocked color=gray]

connection: start-a
connection: a-b [max_link_capacity=2]
connection: b-c
connection: c-end
connection: start-d
connection: d-end
```

**Zone types:**

| Zone type    | Behavior                                                                    |
|--------------|-----------------------------------------------------------------------------|
| `normal`     | Standard zone — drones move through it freely.                              |
| `priority`   | Costs 1 turn and is preferred when equal-cost paths are compared.             |
| `restricted` | Harder to cross — higher cost and triggers an in-transit state for the drone.|
| `blocked`    | Inaccessible — excluded from all valid paths.                               |

**Zone metadata:**

| Key          | Description                                              | Default  |
|--------------|----------------------------------------------------------|----------|
| `zone`       | Zone type (see above)                                    | `normal` |
| `color`      | Display color in the GUI                                 | none     |
| `max_drones` | Maximum simultaneous drones allowed in the zone          | `1`      |

**Connection metadata:**

| Key                 | Description                                                   | Default |
|---------------------|---------------------------------------------------------------|---------|
| `max_link_capacity` | Maximum drones that may use this connection in the same turn  | `1`     |

---

## Algorithm Explanation

### Pathfinding — Dijkstra with cost weighting

The pathfinding module is implemented in `src/Pathfinding/dijkstra.py`. A modified Dijkstra's algorithm is used to find valid routes from the start hub to the end hub across the zone graph.

**Design decisions:**

- **Blocked zones are excluded** — they are never added to the priority queue, so they cannot appear in any valid path.
- **Zone cost weighting** — `restricted` zones cost 2. Other accessible zones cost 1. When routes have the same movement cost, Dijkstra prefers the route containing more `priority` zones.
- **Multi-path discovery** — `find_paths()` creates unique simple alternatives through spur searches with temporary edge and zone bans. The simulator requests up to 35 paths.
- **PathNotFoundError** — if no valid path exists (e.g., all routes pass through blocked zones or no connections link start to end), this exception is raised and the simulation aborts with a clear error message.

The `Dijkstra` class exposes two public methods:

- `find_path()` — returns the single lowest-cost valid path.
- `find_paths(max_paths=6)` — returns several valid low-cost paths; callers may request another limit.

### Simulation engine — turn-based conflict resolution

The simulation runs in discrete turns inside `src/Simulation/simulator.py`. Each turn follows this sequence:

1. Each active drone evaluates its next intended move based on its assigned path.
2. All movement intents are sorted by route progress, zone priority, restricted status, wait time, and drone ID.
3. The `CapacityManager` checks each intent against zone occupancy limits and link capacity limits.
4. Approved movements are applied; rejected drones wait and retry next turn.
5. Drones that reach the end hub are marked as delivered.
6. Drones traversing restricted zones enter an in-transit state and require an extra turn to exit.

**Route spreading:** The `RouteManager` assigns drones to different available paths rather than forcing all drones into a single route. This distributes load and reduces conflicts.

**Conflict resolution:** The capacity manager reserves available zone entries, zone exits, and links in priority order. Rejected drones wait and retry.

### Architecture overview

```
src/
├── Models/          — Zone and graph dataclasses
├── Parser/          — Declaration parsing and whole-map validation
├── Pathfinding/     — Dijkstra and alternative-path discovery
├── Simulation/      — State, capacity resolution, routing, and turns
├── Utils/           — Shared graph, mapping, path, and ID helpers
└── Visualization/   — Tkinter layout, drawing, state, and controls
```

### Shared utilities

Common operations used across multiple modules are centralized in
`src/Utils/` to avoid repeating low-level implementation details.

| File                | Responsibility                                                   |
|---------------------|------------------------------------------------------------------|
| `adjacency.py`      | Builds bidirectional adjacency lists from nodes and edges.       |
| `connection_key.py` | Creates stable unordered keys for bidirectional connections.     |
| `drone_ids.py`      | Provides the project's one-based drone ID range.                 |
| `mappings.py`       | Updates counters and appends values to grouped mappings.         |
| `paths.py`          | Finds path suffixes and the next item after a path position.     |

These helpers are exported through `src.Utils` and are used by the graph,
parser, simulation, routing, and visualization layers.

---

## Visual Representation

The graphical interface is built with Tkinter and located in `src/Visualization/`. Its main components are:

| File                    | Responsibility                                                       |
|-------------------------|----------------------------------------------------------------------|
| `graphical_renderer.py` | Main GUI controller — wires canvas, panel, and simulation together.  |
| `graph_canvas.py`       | Draws static UI, zones, connections, labels, and drone positions.     |
| `canvas_layout.py`      | Calculates responsive panel and graph coordinates.                    |
| `drone_renderer.py`     | Draws compact drone markers.                                           |
| `simulation_panel.py`   | Renders the sidebar: turn counter, drone stats, routes, and controls. |
| `visual_state.py`       | Stores snapshots of each turn for backward navigation.               |

### How the interface enhances the user experience

**Graph canvas** — Zones are drawn as colored circles at their declared `(x, y)` coordinates. Explicit `color` metadata is used when present; otherwise, role and zone-type defaults are applied. Connections are drawn as lines between zones. Drone icons appear on their current zone and move each time the user steps forward.

**Step-by-step navigation** — Playback controls allow stepping forward one turn at a time, stepping backward (via stored snapshots), playing automatically at a fixed interval, pausing, and resetting to turn zero. This makes it easy to inspect exactly what happened at each turn.

**Sidebar panel** — Displays the current turn number, delivered and remaining counts, a progress bar, and the available paths.

**Legend** — A built-in legend explains zone type colors so users can read any map without prior knowledge of the format.

---

## Example Input and Output

**Illustrative input map:**

```text
nb_drones: 3

start_hub: start 0 0 [color=green]
end_hub: end 6 0 [color=red]

hub: a 2 0 [zone=normal color=blue max_drones=1]
hub: b 4 0 [zone=normal color=blue max_drones=1]

connection: start-a
connection: a-b
connection: b-end
```

**Expected terminal output** (one movement line per turn):

```text
D1-a

D1-b D2-a

D1-end D2-b D3-a

D2-end D3-b

D3-end
```

Each entry uses the format `D<id>-<destination>`. Drones that cannot move in a turn are not printed. For restricted-zone transitions, the format is `D<id>-<from>-<to>`.

---

## Project Structure

```text
fly_in/
├── main.py
├── Makefile
├── README.md
├── requirements.txt
├── maps/
│   ├── easy/
│   ├── medium/
│   ├── hard/
│   ├── challenger/
│   ├── valid/
│   └── invalid/
├── src/
│   ├── Models/
│   │   └── graph.py
│   ├── Parser/
│   │   ├── declaration_parser.py
│   │   ├── map_parser.py
│   │   └── map_validator.py
│   ├── Pathfinding/
│   │   └── dijkstra.py
│   ├── Simulation/
│   │   ├── capacity_manager.py
│   │   ├── drone_manager.py
│   │   ├── route_manager.py
│   │   └── simulator.py
│   ├── Utils/
│   │   ├── adjacency.py
│   │   ├── connection_key.py
│   │   ├── drone_ids.py
│   │   ├── mappings.py
│   │   └── paths.py
│   └── Visualization/
│       ├── canvas_layout.py
│       ├── drone_renderer.py
│       ├── graph_canvas.py
│       ├── graphical_renderer.py
│       ├── simulation_panel.py
│       └── visual_state.py
└── tests/
    ├── conftest.py
    ├── test_characterization.py
    ├── test_parser_errors.py
    ├── test_capacity_rules.py
    ├── test_simulation_behavior.py
    ├── test_utils.py
    └── test_benchmarks.py
```

---

## Makefile Commands

| Command               | Description                                   |
|-----------------------|-----------------------------------------------|
| `make install`        | Install project dependencies.                 |
| `make run`            | Run the GUI simulation with the default map.  |
| `make run MAP=<path>` | Run the GUI simulation with a selected map.   |
| `make debug`          | Run the project with Python debugger.         |
| `make test`           | Run all tests with pytest.                    |
| `make lint`           | Run flake8 and mypy.                          |
| `make lint-strict`    | Run flake8 and strict mypy.                   |
| `make clean`          | Remove cache and temporary files.             |

---

## Resources

### References

- [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) — the shortest-path algorithm at the core of the pathfinding module.
- [Graph theory](https://en.wikipedia.org/wiki/Graph_theory) — foundational concepts for the zone network model.
- [Multi-agent pathfinding](https://en.wikipedia.org/wiki/Multi-agent_pathfinding) — background on coordinating multiple agents through a shared graph.
- [Discrete-event simulation](https://en.wikipedia.org/wiki/Discrete-event_simulation) — the turn-based model used by the simulator.
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) — used for Zone, Connection, and Drone models.
- [Python heapq](https://docs.python.org/3/library/heapq.html) — used in the Dijkstra priority queue.
- [Tkinter documentation](https://docs.python.org/3/library/tkinter.html) — the GUI toolkit used for visualization.
- [pytest documentation](https://docs.pytest.org/) — test framework.
- [mypy documentation](https://mypy.readthedocs.io/) — static type checker.
- [flake8 documentation](https://flake8.pycqa.org/) — linting tool.

### AI Usage

AI tools (Claude by Anthropic) were used during development for the following tasks:

- **README writing and documentation structure** — drafting and restructuring the README sections to meet project requirements.
- **Architecture review** — reviewing the simulation and pathfinding module design and suggesting clearer separation of responsibilities between `simulator.py`, `drone_manager.py`, `capacity_manager.py`, and `route_manager.py`.
- **Tkinter refactoring ideas** — suggesting how to split the visualization layer into focused components (`graph_canvas.py`, `simulation_panel.py`, `visual_state.py`) to reduce coupling.
- **Debugging support** — helping trace edge cases in capacity conflict resolution and restricted-zone transit logic during development.

All AI-assisted suggestions were reviewed, understood, tested, and manually integrated by the author.

---

<div align="center">
<sub>Made with Python, Tkinter, drones, graphs, and a lot of pathfinding.</sub>
</div>
