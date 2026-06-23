"""Renderer for drone markers displayed over the graph canvas."""

from __future__ import annotations

import tkinter as tk

from src.Visualization.canvas_layout import CanvasLayout
from src.Visualization.visual_state import DronePositions, DroneStatuses
from src.Utils.mappings import append_to_group


class DroneRenderer:
    """Draw waiting and moving drones as compact black markers."""

    def __init__(
        self,
        canvas: tk.Canvas,
        layout: CanvasLayout,
    ) -> None:
        """Store the canvas and layout information used to place drones."""
        self.canvas = canvas
        self.layout = layout

    def draw_drones_positions(
        self,
        positions: DronePositions,
        statuses: DroneStatuses | None = None,
    ) -> None:
        """Draw drones from explicit canvas coordinates.

        Drones sharing the same rounded position are represented by one marker
        plus a small count label, exactly like the original implementation.
        """
        self.canvas.delete("drone")

        position_groups: dict[tuple[int, int], list[int]] = {}

        for drone_id, position in positions.items():
            if position is None:
                continue

            key = (round(position[0]), round(position[1]))
            append_to_group(position_groups, key, drone_id)

        for drone_ids in position_groups.values():
            sorted_ids = sorted(drone_ids)
            first_id = sorted_ids[0]
            position = positions[first_id]

            if position is None:
                continue

            status = "waiting"
            if statuses is not None:
                status = statuses.get(first_id, "waiting")

            x_pos, y_pos = position

            self.draw_single_drone(
                x_pos,
                y_pos,
                drone_id=first_id,
                status=status,
                count=len(sorted_ids),
            )

    def draw_single_drone(
        self,
        x_pos: float,
        y_pos: float,
        drone_id: int,
        status: str,
        count: int = 1,
    ) -> None:
        """Draw one drone marker and an optional grouped-count label."""
        outer_radius = self.layout.drone_radius + 3
        inner_radius = self.layout.drone_radius

        self.canvas.create_oval(
            x_pos - outer_radius,
            y_pos - outer_radius,
            x_pos + outer_radius,
            y_pos + outer_radius,
            fill="#F8FAFC",
            outline="#111827",
            width=1,
            tags="drone",
        )

        self.canvas.create_oval(
            x_pos - inner_radius,
            y_pos - inner_radius,
            x_pos + inner_radius,
            y_pos + inner_radius,
            fill="#111827",
            outline="#111827",
            width=1,
            tags="drone",
        )

        if count <= 1:
            return

        self.canvas.create_text(
            x_pos + outer_radius + 9,
            y_pos,
            text=f"x{count}",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            fill="#111827",
            tags="drone",
        )

    def get_offset_position(
        self,
        center_x: float,
        center_y: float,
        index: int,
        total: int,
    ) -> tuple[float, float]:
        """Return the original compact drone position without extra offset."""
        return center_x, center_y
