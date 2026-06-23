"""Responsive layout logic for the Fly-in graph canvas.

This module owns only geometry-related state: canvas dimensions, panel
bounds, graph scale, graph offsets, node positions, and density rules.
It does not draw Tkinter items directly.
"""

from __future__ import annotations

import tkinter as tk

from src.Models.graph import Graph


class CanvasLayout:
    """Calculate sizes and coordinates used by the canvas renderers.

    The constants in this class come from the original GraphCanvas class.
    They should stay unchanged unless the intention is to deliberately alter
    the visual layout.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        graph: Graph,
        window_width: int,
        window_height: int,
        sidebar_width: int,
    ) -> None:
        """Store canvas references and original layout values."""
        self.canvas = canvas
        self.graph = graph
        self.window_width = window_width
        self.window_height = window_height
        self.sidebar_width = sidebar_width

        self.outer_padding = 26
        self.content_gap = 26
        self.header_height = 118

        self.node_radius = 30
        self.drone_radius = 9
        self.scale = 100.0
        self.offset_x = 100.0
        self.offset_y = 100.0

        self.node_positions: dict[str, tuple[float, float]] = {}

        self.zone_label_font_size = 10
        self.capacity_font_size = 9
        self.max_zone_label_chars = 16
        self.show_connection_badges = True
        self.show_all_zone_labels = True

    def update_canvas_size(self, width: int, height: int) -> bool:
        """Save a real Tkinter canvas size when it is large enough to use."""
        if width <= 10 or height <= 10:
            return False

        if width == self.window_width and height == self.window_height:
            return False

        self.window_width = width
        self.window_height = height
        return True

    def effective_sidebar_width(self) -> int:
        """Return the responsive sidebar width used by the original layout."""
        real_width = max(self.canvas.winfo_width(), self.window_width)
        sidebar_width = int(real_width * 0.24)
        return max(520, min(sidebar_width, 820))

    def graph_bounds(self) -> tuple[int, int, int, int]:
        """Return the left, top, right and bottom limits of the graph panel."""
        sidebar_width = self.effective_sidebar_width()

        graph_left = self.outer_padding
        graph_top = self.outer_padding
        graph_right = (
            self.window_width
            - sidebar_width
            - self.outer_padding
            - self.content_gap
        )
        graph_bottom = self.window_height - self.outer_padding

        return graph_left, graph_top, graph_right, graph_bottom

    def sidebar_bounds(self) -> tuple[int, int, int, int]:
        """Return the sidebar panel limits."""
        sidebar_width = self.effective_sidebar_width()
        side_right = self.window_width - self.outer_padding
        side_left = side_right - sidebar_width

        return (
            side_left,
            self.outer_padding,
            side_right,
            self.window_height - self.outer_padding,
        )

    def compute_layout(self) -> None:
        """Fit graph coordinates inside the graph panel.

        This method preserves the original scale and offset calculation.
        It first adapts visual density according to the number of zones, then
        maps graph coordinates into the available panel area.
        """
        if not self.graph.zones:
            return

        self._configure_density()

        xs = [zone.x for zone in self.graph.zones.values()]
        ys = [zone.y for zone in self.graph.zones.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        graph_left, graph_top, graph_right, graph_bottom = self.graph_bounds()

        margin_x = max(120, self.node_radius * 3.5)
        margin_y = max(82, self.node_radius * 3.2)

        usable_left = graph_left + margin_x
        usable_right = graph_right - margin_x
        usable_top = graph_top + self.header_height + margin_y - 22
        usable_bottom = graph_bottom - margin_y

        available_w = max(usable_right - usable_left, 1)
        available_h = max(usable_bottom - usable_top, 1)

        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        scale_x = available_w / span_x
        scale_y = available_h / span_y

        if span_y <= 1:
            self.scale = min(scale_x * 0.94, 285)
        elif span_y <= 2:
            self.scale = min(scale_x * 0.90, scale_y * 1.08, 280)
        else:
            self.scale = min(scale_x * 1.08, scale_y * 1.12, 265)

        graph_center_x = (min_x + max_x) / 2
        graph_center_y = (min_y + max_y) / 2

        canvas_center_x = (usable_left + usable_right) / 2
        canvas_center_y = (usable_top + usable_bottom) / 2 - 10

        self.offset_x = canvas_center_x - graph_center_x * self.scale
        self.offset_y = canvas_center_y + graph_center_y * self.scale

    def _configure_density(self) -> None:
        """Adjust node, drone, label and badge sizes by graph density."""
        zone_count = len(self.graph.zones)

        self.node_radius = 30
        self.drone_radius = 9
        self.zone_label_font_size = 10
        self.capacity_font_size = 9
        self.max_zone_label_chars = 16
        self.show_connection_badges = True
        self.show_all_zone_labels = True

        if zone_count >= 45:
            self.node_radius = 19
            self.drone_radius = 6
            self.zone_label_font_size = 7
            self.capacity_font_size = 7
            self.max_zone_label_chars = 8
            self.show_connection_badges = False
            self.show_all_zone_labels = False
        elif zone_count >= 25:
            self.node_radius = 22
            self.drone_radius = 7
            self.zone_label_font_size = 8
            self.capacity_font_size = 8
            self.max_zone_label_chars = 10
            self.show_connection_badges = False
        elif zone_count >= 15:
            self.node_radius = 25
            self.drone_radius = 8
            self.zone_label_font_size = 9
            self.capacity_font_size = 8
            self.max_zone_label_chars = 12

    def transform(self, x_coord: int, y_coord: int) -> tuple[float, float]:
        """Convert graph coordinates into Tkinter canvas coordinates."""
        return (
            x_coord * self.scale + self.offset_x,
            -y_coord * self.scale + self.offset_y,
        )
