"""Draw the Fly-in graph, static interface, and drone markers."""

from __future__ import annotations

import tkinter as tk

from src.Models.graph import Graph, Zone
from src.Visualization.canvas_layout import CanvasLayout
from src.Visualization.drone_renderer import DroneRenderer
from src.Visualization.visual_state import DronePositions, DroneStatuses


def _draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    fill: str,
    outline: str,
    width: int = 1,
    tags: str | tuple[str, ...] | None = None,
) -> int:
    """Draw a rounded rectangle using a smooth polygon."""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=24,
        fill=fill,
        outline=outline,
        width=width,
        tags=() if tags is None else tags,
    )


class GraphCanvas:
    """Coordinate responsive layout and all graph-canvas drawing."""

    def __init__(
        self,
        window: tk.Tk,
        graph: Graph,
        colors: dict[str, str],
        window_width: int,
        window_height: int,
        sidebar_width: int,
    ) -> None:
        """Create the canvas and its layout and drone helpers."""
        self.graph = graph
        self.colors = colors
        self.canvas = tk.Canvas(
            window,
            width=window_width,
            height=window_height,
            bg=colors["app_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.layout = CanvasLayout(
            self.canvas,
            graph,
            window_width,
            window_height,
            sidebar_width,
        )
        self.drone_renderer = DroneRenderer(self.canvas, self.layout)

    def update_canvas_size(self, width: int, height: int) -> bool:
        """Update the responsive canvas dimensions."""
        return self.layout.update_canvas_size(width, height)

    def set_graph(self, graph: Graph) -> None:
        """Replace the graph and recompute its layout."""
        self.graph = graph
        self.layout.graph = graph
        self.layout.node_positions.clear()
        self.layout.compute_layout()

    def draw_base_ui(self) -> None:
        """Clear and redraw the static background panels and titles."""
        self.canvas.delete("all")
        graph_left, graph_top, graph_right, graph_bottom = (
            self.layout.graph_bounds()
        )
        side_left, side_top, side_right, side_bottom = (
            self.layout.sidebar_bounds()
        )

        _draw_rounded_rect(
            self.canvas,
            graph_left,
            graph_top,
            graph_right,
            graph_bottom,
            radius=22,
            fill=self.colors["graph_bg"],
            outline=self.colors["graph_border"],
        )
        _draw_rounded_rect(
            self.canvas,
            side_left,
            side_top,
            side_right,
            side_bottom,
            radius=22,
            fill=self.colors["panel_bg"],
            outline=self.colors["sidebar_border"],
        )

        self.canvas.create_text(
            graph_left + 34,
            graph_top + 42,
            text="Fly-in Simulation",
            anchor="w",
            font=("Segoe UI", 24, "bold"),
            fill=self.colors["text_dark"],
        )
        self.canvas.create_text(
            graph_left + 34,
            graph_top + 76,
            text="Real-time graph view",
            anchor="w",
            font=("Segoe UI", 11),
            fill=self.colors["text_muted_dark"],
        )
        self.canvas.create_text(
            side_left + 32,
            side_top + 48,
            text="Simulation Panel",
            anchor="w",
            font=("Segoe UI", 25, "bold"),
            fill=self.colors["text_primary"],
        )
        self.canvas.create_text(
            side_left + 32,
            side_top + 86,
            text="Status, paths and controls",
            anchor="w",
            font=("Segoe UI", 10),
            fill=self.colors["text_muted"],
        )

    def draw_graph(self) -> None:
        """Draw connections, zones, and labels in stable layer order."""
        self.layout.node_positions.clear()
        for zone_name, zone in self.graph.zones.items():
            self.layout.node_positions[zone_name] = self.layout.transform(
                zone.x,
                zone.y,
            )

        self._draw_edges()
        for zone_name, zone in self.graph.zones.items():
            self._draw_zone(zone_name, zone)
        self._draw_zone_labels()

    def _draw_edges(self) -> None:
        """Draw graph connections and optional capacity badges."""
        for connection in self.graph.connections:
            zone_a = self.graph.get_zone(connection.zone_a)
            zone_b = self.graph.get_zone(connection.zone_b)
            x1, y1 = self.layout.transform(zone_a.x, zone_a.y)
            x2, y2 = self.layout.transform(zone_b.x, zone_b.y)
            line_color = (
                self.colors["line_highlight"]
                if connection.max_link_capacity > 1
                else self.colors["line_default"]
            )
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                width=2,
                fill=line_color,
                capstyle="round",
                arrow="last",
                arrowshape=(9, 11, 4),
            )
            if self.layout.show_connection_badges:
                self._draw_connection_badge(
                    x1,
                    y1,
                    x2,
                    y2,
                    connection.max_link_capacity,
                )

    def _draw_connection_badge(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        capacity: int,
    ) -> None:
        """Draw a connection-capacity badge."""
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        radius = max(9, self.layout.node_radius * 0.36)
        self.canvas.create_oval(
            mid_x - radius,
            mid_y - radius,
            mid_x + radius,
            mid_y + radius,
            fill=self.colors["badge_bg"],
            outline=self.colors["badge_border"],
            width=1,
        )
        self.canvas.create_text(
            mid_x,
            mid_y,
            text=str(capacity),
            anchor="center",
            font=("Segoe UI", self.layout.capacity_font_size, "bold"),
            fill=self.colors["badge_text"],
        )

    def _draw_zone(self, zone_name: str, zone: Zone) -> None:
        """Draw one zone node and its optional role ring."""
        x_pos, y_pos = self.layout.node_positions[zone_name]
        if zone.name == self.graph.start:
            self._draw_zone_ring(x_pos, y_pos, "#A7F3D0")
        elif zone.name == self.graph.end:
            self._draw_zone_ring(x_pos, y_pos, "#FECACA")

        self.canvas.create_oval(
            x_pos - self.layout.node_radius,
            y_pos - self.layout.node_radius,
            x_pos + self.layout.node_radius,
            y_pos + self.layout.node_radius,
            fill=self._zone_color(zone),
            outline="#1F2937",
            width=2,
        )

    def _draw_zone_ring(
        self,
        x_pos: float,
        y_pos: float,
        color: str,
    ) -> None:
        """Draw the outer ring used by start and end zones."""
        radius = self.layout.node_radius + 7
        self.canvas.create_oval(
            x_pos - radius,
            y_pos - radius,
            x_pos + radius,
            y_pos + radius,
            outline=color,
            width=2,
        )

    def _draw_zone_labels(self) -> None:
        """Draw labels allowed by the active density settings."""
        for zone_name, zone in self.graph.zones.items():
            if (
                not self.layout.show_all_zone_labels
                and zone.name not in {self.graph.start, self.graph.end}
            ):
                continue

            x_pos, y_pos = self.layout.node_positions[zone_name]
            label = zone_name
            if len(label) > self.layout.max_zone_label_chars:
                label = (
                    f"{label[:self.layout.max_zone_label_chars - 1]}\u2026"
                )
            self.canvas.create_text(
                x_pos,
                y_pos,
                text=label,
                anchor="center",
                font=("Segoe UI", self.layout.zone_label_font_size, "bold"),
                fill=self._zone_text_color(zone),
            )

    def _zone_color(self, zone: Zone) -> str:
        """Return the fill color for a zone."""
        if zone.color != "none":
            return zone.color
        if zone.name == self.graph.start:
            return self.colors["zone_start"]
        if zone.name == self.graph.end:
            return self.colors["zone_end"]
        return self.colors[f"zone_{zone.zone_type}"]

    def _zone_text_color(self, zone: Zone) -> str:
        """Return a readable text color for a zone."""
        if zone.zone_type in {"priority", "restricted"}:
            return "#111827"
        if zone.name == self.graph.start:
            return "#052E16"
        return "#F8FAFC"

    def draw_drones_positions(
        self,
        positions: DronePositions,
        statuses: DroneStatuses | None = None,
    ) -> None:
        """Draw drones from explicit canvas positions."""
        self.drone_renderer.draw_drones_positions(positions, statuses)
