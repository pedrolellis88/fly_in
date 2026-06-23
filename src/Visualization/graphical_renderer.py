"""Tkinter controller for Fly-in rendering, controls, and animation."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable

from src.Models.graph import Graph
from src.Simulation.simulator import Simulator
from src.Utils.drone_ids import iter_drone_ids
from src.Visualization.graph_canvas import GraphCanvas
from src.Visualization.simulation_panel import SimulationPanel
from src.Visualization.visual_state import (
    DronePositions,
    RendererSnapshot,
    VisualStateManager,
)


DEFAULT_COLORS: dict[str, str] = {
    "app_bg": "#0b0f17",
    "panel_bg": "#151a23",
    "card_bg": "#1d2430",
    "graph_bg": "#f5f7fb",
    "graph_border": "#d8dee9",
    "sidebar_border": "#2b3444",
    "text_primary": "#f4f7fb",
    "text_secondary": "#b9c2d0",
    "text_muted": "#b9c2d0",
    "text_dark": "#1f2937",
    "text_muted_dark": "#6b7280",
    "line_default": "#4c5870",
    "line_highlight": "#4c84ff",
    "zone_normal": "#9fd0ff",
    "zone_start": "#39c87d",
    "zone_end": "#ff6b57",
    "zone_restricted": "#ff00ff",
    "zone_priority": "#ffd84d",
    "zone_blocked": "#939bad",
    "badge_bg": "#ffffff",
    "badge_border": "#c8d1df",
    "badge_text": "#1a2332",
    "control_bg": "#2a3447",
    "control_hover": "#36425a",
    "danger_bg": "#5a2930",
    "danger_hover": "#743540",
    "progress_track": "#2a3447",
    "progress_fill": "#39c87d",
    "accent": "#7fb0ff",
    "drone_waiting": "#111827",
}


class GraphicalRenderer:
    """Render and control the Fly-in simulation."""

    def __init__(
        self,
        graph: Graph,
        map_path: Path,
        simulator_builder: Callable[[Path], Simulator],
    ) -> None:
        """Initialize the window, drawing modules, and playback state."""
        self.graph = graph
        self.map_path = map_path
        self.simulator_builder = simulator_builder
        self.simulator: Simulator | None = None

        self.window_width = 1600
        self.window_height = 900
        self.sidebar_width = 380
        self.is_playing = False
        self.is_animating = False
        self.play_delay_ms = 550
        self.animation_frames = 14
        self.animation_delay_ms = 34
        self.just_arrived_drones: set[int] = set()
        self.history: list[RendererSnapshot] = []
        self.colors = DEFAULT_COLORS.copy()

        self.window = tk.Tk()
        self.window.title("Fly-in Simulation")
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.window.minsize(1280, 720)
        self.window.configure(bg=self.colors["app_bg"])
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()
        self.graph_canvas = GraphCanvas(
            self.window,
            graph,
            self.colors,
            self.window_width,
            self.window_height,
            self.sidebar_width,
        )
        self.panel = SimulationPanel(
            self.window,
            self.graph_canvas.canvas,
            self.colors,
            self.graph_canvas.layout.sidebar_bounds(),
            self.sidebar_width,
        )
        self.state = VisualStateManager()
        self.graph_canvas.canvas.bind("<Configure>", self._on_canvas_resize)
        self._draw_full_static_ui()

    def _configure_styles(self) -> None:
        """Configure the ttk styles used by sidebar controls."""
        self.style.configure(
            "Sidebar.TFrame",
            background=self.colors["card_bg"],
        )
        self._configure_button_style(
            "Control.TButton",
            self.colors["control_bg"],
            self.colors["control_hover"],
        )
        self._configure_button_style(
            "Danger.TButton",
            self.colors["danger_bg"],
            self.colors["danger_hover"],
        )

    def _configure_button_style(
        self,
        name: str,
        background: str,
        hover: str,
    ) -> None:
        """Configure one sidebar button style."""
        self.style.configure(
            name,
            font=("Segoe UI", 11, "bold"),
            padding=(10, 9),
            background=background,
            foreground=self.colors["text_primary"],
            borderwidth=0,
            relief="flat",
        )
        self.style.map(
            name,
            background=[("active", hover), ("pressed", hover)],
        )

    def _on_canvas_resize(self, event: Any) -> None:
        """Redraw the interface after a usable canvas size change."""
        if not self.graph_canvas.update_canvas_size(
            int(event.width),
            int(event.height),
        ):
            return

        self._draw_full_static_ui()
        self._draw_dynamic_ui()

    def attach_simulator(self, simulator: Simulator) -> None:
        """Attach a simulator and reset renderer history."""
        self.simulator = simulator
        self.graph = simulator.graph
        self.graph_canvas.set_graph(simulator.graph)
        self.history = []
        self.just_arrived_drones.clear()
        self._draw_full_static_ui()
        self._draw_dynamic_ui()

    def update(self) -> None:
        """Refresh pending Tkinter work."""
        self.window.update_idletasks()
        self.window.update()

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.window.mainloop()

    def _draw_full_static_ui(self) -> None:
        """Compute layout and draw static graph and panel elements."""
        self.graph_canvas.layout.compute_layout()
        self.graph_canvas.draw_base_ui()
        self.graph_canvas.draw_graph()
        self.panel.sidebar_bounds = (
            self.graph_canvas.layout.sidebar_bounds()
        )
        self.panel.draw_static(
            self.back_turn,
            self.next_turn,
            self.play,
            self.pause,
            self.reset,
            self.window.destroy,
        )

    def _draw_dynamic_ui(self) -> None:
        """Draw simulator-dependent status, paths, and drones."""
        if self.simulator is None:
            return

        self.panel.draw_status(self.simulator)
        self.panel.draw_paths(self.simulator.get_available_paths())
        self.graph_canvas.draw_drones_positions(
            self._snapshot_positions(include_arrivals=False),
        )

    def _snapshot_positions(
        self,
        include_arrivals: bool,
    ) -> DronePositions:
        """Return current canvas positions for every drone."""
        if self.simulator is None:
            return {}

        positions: DronePositions = {}
        nodes = self.graph_canvas.layout.node_positions
        drones = self.simulator.drones
        groups = self.state.group_drones_by_zone(self.simulator)

        for zone_name, drone_ids in groups.items():
            if zone_name not in nodes:
                continue

            center = nodes[zone_name]
            for drone_id in drone_ids:
                positions[drone_id] = center

        for drone_id in iter_drone_ids(drones.nb_drones):
            if drones.is_delivered(drone_id):
                positions[drone_id] = (
                    nodes[self.graph.end]
                    if include_arrivals
                    and drone_id in self.just_arrived_drones
                    else None
                )
                continue

            if not drones.is_in_transit(drone_id):
                continue

            label = drones.get_connection_label(drone_id)
            if label is None:
                positions[drone_id] = None
                continue

            start_zone, target_zone = label.split("-", maxsplit=1)
            if start_zone not in nodes or target_zone not in nodes:
                positions[drone_id] = None
                continue

            x1, y1 = nodes[start_zone]
            x2, y2 = nodes[target_zone]
            positions[drone_id] = ((x1 + x2) / 2, (y1 + y2) / 2)

        return positions

    def _snapshot_positions_for_back(self) -> DronePositions:
        """Return positions that show delivered drones at the end node."""
        positions = self._snapshot_positions(include_arrivals=False)
        if self.simulator is None:
            return positions

        goal = self.graph_canvas.layout.node_positions[self.graph.end]
        for drone_id in iter_drone_ids(self.simulator.nb_drones):
            if self.simulator.drones.is_delivered(drone_id):
                positions[drone_id] = goal
        return positions

    def animate_between_states(
        self,
        start_positions: DronePositions,
        end_positions: DronePositions,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Animate all drones simultaneously between two visual states."""
        if self.simulator is None:
            return

        self.is_animating = True

        def frame(step: int) -> None:
            """Draw one interpolation frame and schedule the next."""
            if self.simulator is None:
                self.is_animating = False
                return

            factor = step / self.animation_frames
            interpolated: DronePositions = {}
            for drone_id in iter_drone_ids(self.simulator.nb_drones):
                start = start_positions.get(drone_id)
                end = end_positions.get(drone_id)
                if end is None:
                    interpolated[drone_id] = None
                elif start is None:
                    interpolated[drone_id] = end
                else:
                    interpolated[drone_id] = (
                        start[0] + (end[0] - start[0]) * factor,
                        start[1] + (end[1] - start[1]) * factor,
                    )

            self.graph_canvas.draw_drones_positions(interpolated)
            self.panel.draw_status(self.simulator)
            self.update()

            if step < self.animation_frames:
                self.window.after(
                    self.animation_delay_ms,
                    lambda: frame(step + 1),
                )
                return

            self.is_animating = False
            self.graph_canvas.draw_drones_positions(end_positions)
            self.panel.draw_status(self.simulator)
            self.update()
            if on_complete is not None:
                on_complete()

        frame(1)

    def _finalize_arrivals(self) -> None:
        """Hide arrivals and schedule the next autoplay turn."""
        self.graph_canvas.draw_drones_positions(
            self._snapshot_positions(include_arrivals=False),
        )
        if self.simulator is None:
            return

        self.panel.draw_status(self.simulator)
        self.update()
        self.just_arrived_drones.clear()
        if self.is_playing:
            self.window.after(self.play_delay_ms, self.next_turn)

    def next_turn(self) -> None:
        """Advance one turn and animate all accepted movements."""
        if self.simulator is None or self.is_animating:
            return
        if self.simulator.drones.all_delivered():
            return

        self.just_arrived_drones.clear()
        self.history.append(self.state.capture(self.simulator))
        previous_positions = self._snapshot_positions(
            include_arrivals=False,
        )
        delivered_before = set(self.simulator.drones.delivered)
        movements = self.simulator.next_turn()
        self.just_arrived_drones = (
            set(self.simulator.drones.delivered) - delivered_before
        )

        if not movements:
            self.panel.draw_status(self.simulator)
            self.update()
            return

        print(" ".join(movements))
        self.animate_between_states(
            previous_positions,
            self._snapshot_positions(include_arrivals=True),
            on_complete=self._finalize_arrivals,
        )

    def back_turn(self) -> None:
        """Restore and animate the previous simulation state."""
        if (
            self.simulator is None
            or self.is_animating
            or not self.history
        ):
            return

        self.pause()
        self.just_arrived_drones.clear()
        current_positions = self._snapshot_positions_for_back()
        self.state.restore(self.simulator, self.history.pop())
        target_positions = self._snapshot_positions(
            include_arrivals=False,
        )

        def on_complete() -> None:
            """Refresh status after backward animation."""
            if self.simulator is not None:
                self.panel.draw_status(self.simulator)
            self.update()

        self.animate_between_states(
            current_positions,
            target_positions,
            on_complete=on_complete,
        )

    def play(self) -> None:
        """Start automatic playback."""
        if self.is_playing:
            return

        self.is_playing = True
        if not self.is_animating:
            self.next_turn()

    def pause(self) -> None:
        """Pause automatic playback."""
        self.is_playing = False

    def reset(self) -> None:
        """Replace the simulator with a fresh instance."""
        self.pause()
        self.just_arrived_drones.clear()
        self.history = []
        self.simulator = self.simulator_builder(self.map_path)
        self.graph = self.simulator.graph
        self.graph_canvas.set_graph(self.graph)
        self._draw_full_static_ui()
        self._draw_dynamic_ui()
        self.update()
