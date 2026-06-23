"""Draw the sidebar panel for the Fly-in renderer."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from src.Simulation.simulator import Simulator


class SimulationPanel:
    """Render and update the sidebar status, paths, legend, and controls."""

    def __init__(
        self,
        window: tk.Tk,
        canvas: tk.Canvas,
        colors: dict[str, str],
        sidebar_bounds: tuple[int, int, int, int],
        sidebar_width: int,
    ) -> None:
        """Initialize the sidebar panel drawing state."""
        self.window = window
        self.canvas = canvas
        self.colors = colors
        self.sidebar_bounds = sidebar_bounds
        self.sidebar_width = sidebar_width

        self.controls_frame: ttk.Frame | None = None
        self.paths_frame: ttk.Frame | None = None
        self.paths_text: tk.Text | None = None

        self._inner_left = 0.0
        self._inner_right = 0.0
        self._card_tops: dict[str, float] = {}
        self._card_bottoms: dict[str, float] = {}

    def draw_static(
        self,
        on_back: Callable[[], None],
        on_next: Callable[[], None],
        on_play: Callable[[], None],
        on_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """Draw static sidebar cards, legend, paths widget, and controls."""
        left, top, right, bottom = self.sidebar_bounds

        pad = 24
        gap = 14

        self._inner_left = left + pad
        self._inner_right = right - pad

        content_top = top + 116
        content_bottom = bottom - 22

        status_h = 150
        legend_h = 166
        controls_h = 172

        status_top = content_top
        status_bottom = status_top + status_h

        legend_top = status_bottom + gap
        legend_bottom = legend_top + legend_h

        controls_bottom = content_bottom
        controls_top = controls_bottom - controls_h

        paths_top = legend_bottom + gap
        paths_bottom = controls_top - gap

        if paths_bottom - paths_top < 104:
            legend_h = 150
            legend_bottom = legend_top + legend_h
            paths_top = legend_bottom + gap
            paths_bottom = controls_top - gap

        self._card_tops = {
            "status": status_top,
            "legend": legend_top,
            "paths": paths_top,
            "controls": controls_top,
        }
        self._card_bottoms = {
            "status": status_bottom,
            "legend": legend_bottom,
            "paths": paths_bottom,
            "controls": controls_bottom,
        }

        self._draw_card(
            self._inner_left,
            status_top,
            self._inner_right,
            status_bottom,
            "Status",
            "↗",
        )
        self._draw_card(
            self._inner_left,
            legend_top,
            self._inner_right,
            legend_bottom,
            "Legend",
            "▣",
        )
        self._draw_card(
            self._inner_left,
            paths_top,
            self._inner_right,
            paths_bottom,
            "Paths",
            "↝",
        )
        self._draw_card(
            self._inner_left,
            controls_top,
            self._inner_right,
            controls_bottom,
            "Controls",
            "⚙",
        )

        self._draw_legend(self._inner_left + 34, legend_top + 62)
        self._draw_paths_widget(paths_top, paths_bottom)
        self._draw_controls(
            on_back,
            on_next,
            on_play,
            on_pause,
            on_reset,
            on_exit,
            controls_top,
            controls_bottom,
        )

    def draw_status(
        self,
        simulator: Simulator,
        visual_delivered_count: int | None = None,
    ) -> None:
        """Draw the current turn, delivery count, and progress bar."""
        self.canvas.delete("status_dynamic")

        card_top = self._card_tops["status"]
        card_bottom = self._card_bottoms["status"]

        real_delivered = len(simulator.drones.delivered)
        total = simulator.nb_drones

        if visual_delivered_count is None:
            delivered = real_delivered
        else:
            delivered = visual_delivered_count

        delivered = max(0, min(delivered, total))
        remaining = max(total - delivered, 0)

        progress = 0.0 if total == 0 else delivered / total
        percent = round(progress * 100)

        left = self._inner_left + 34
        right = self._inner_right - 34

        self.canvas.create_text(
            left,
            card_top + 62,
            text=f"Turn {simulator.turn}",
            anchor="w",
            font=("Segoe UI", 18, "bold"),
            fill=self.colors["text_primary"],
            tags="status_dynamic",
        )

        self.canvas.create_text(
            right,
            card_top + 62,
            text=f"{percent}%",
            anchor="e",
            font=("Segoe UI", 21, "bold"),
            fill=self.colors["progress_fill"],
            tags="status_dynamic",
        )

        self.canvas.create_text(
            left,
            card_top + 94,
            text=f"{delivered}/{total} delivered",
            anchor="w",
            font=("Segoe UI", 11),
            fill=self.colors["text_secondary"],
            tags="status_dynamic",
        )

        self.canvas.create_text(
            right,
            card_top + 94,
            text=f"{remaining} remaining",
            anchor="e",
            font=("Segoe UI", 11),
            fill=self.colors["text_muted"],
            tags="status_dynamic",
        )

        bar_x1 = left
        bar_x2 = right
        bar_y1 = card_bottom - 34
        bar_y2 = bar_y1 + 16

        self._draw_rounded_rect(
            bar_x1,
            bar_y1,
            bar_x2,
            bar_y2,
            radius=8,
            fill=self.colors["progress_track"],
            outline=self.colors["progress_track"],
            tags="status_dynamic",
        )

        if progress > 0:
            fill_x2 = bar_x1 + (bar_x2 - bar_x1) * progress

            self._draw_rounded_rect(
                bar_x1,
                bar_y1,
                fill_x2,
                bar_y2,
                radius=8,
                fill=self.colors["progress_fill"],
                outline=self.colors["progress_fill"],
                tags="status_dynamic",
            )

        marker_radius = 6
        marker_x = bar_x1 + (bar_x2 - bar_x1) * progress
        marker_x = max(
            bar_x1 + marker_radius,
            min(marker_x, bar_x2 - marker_radius),
        )

        self.canvas.create_oval(
            marker_x - marker_radius,
            (bar_y1 + bar_y2) / 2 - marker_radius,
            marker_x + marker_radius,
            (bar_y1 + bar_y2) / 2 + marker_radius,
            fill="#F8FAFC",
            outline=self.colors["progress_fill"],
            width=2,
            tags="status_dynamic",
        )

    def draw_paths(self, paths: list[list[str]]) -> None:
        """Update the paths text widget with available routes."""
        if self.paths_text is None:
            return

        lines = self._build_path_lines(paths)
        self.paths_text.configure(state="normal")
        self.paths_text.delete("1.0", "end")
        self.paths_text.insert("1.0", "\n".join(lines))
        self.paths_text.configure(state="disabled")

        if hasattr(self, "paths_scrollbar"):
            if len(lines) > 5:
                self.paths_text.configure(
                    yscrollcommand=self.paths_scrollbar.set
                )
                self.paths_scrollbar.configure(command=self.paths_text.yview)
                self.paths_scrollbar.pack(side="right", fill="y")
            else:
                self.paths_scrollbar.pack_forget()
                self.paths_text.configure()

    def _build_path_lines(self, paths: list[list[str]]) -> list[str]:
        """Return formatted text lines for the available paths list."""
        if not paths:
            return ["No available paths loaded."]

        if len(paths) > 150:
            return [
                f"{len(paths)} available paths",
                "Too many paths to list safely.",
                "Showing compact summary.",
            ]

        return [
            self._format_path(index + 1, path)
            for index, path in enumerate(paths)
        ]

    def _format_path(self, index: int, path: list[str]) -> str:
        """Return one compact display line for a path."""
        text = " → ".join(path)
        if len(text) > 72:
            text = f"{text[:69]}..."
        return f"{index:02d}. {text}"

    def _draw_paths_widget(self, card_top: float, card_bottom: float) -> None:
        """Create the embedded text widget used to display available paths."""
        if self.paths_frame is not None:
            self.paths_frame.destroy()

        frame_x = self._inner_left + 64
        frame_y = card_top + 52
        frame_w = self._inner_right - frame_x - 24
        frame_h = max(card_bottom - frame_y - 14, 72)

        self.paths_frame = ttk.Frame(self.window, style="Sidebar.TFrame")

        self.paths_scrollbar = ttk.Scrollbar(
            self.paths_frame,
            orient="vertical",
        )

        self.paths_text = tk.Text(
            self.paths_frame,
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            insertbackground=self.colors["text_secondary"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
            font=("Segoe UI", 10),
            padx=0,
            pady=0,
        )
        self.paths_text.pack(side="left", fill="both", expand=True)
        self.paths_text.configure(state="disabled")

        self.canvas.create_window(
            frame_x,
            frame_y,
            anchor="nw",
            window=self.paths_frame,
            width=frame_w,
            height=frame_h,
        )

    def _draw_card(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        title: str,
        icon: str,
    ) -> None:
        """Draw one sidebar card with an icon and title."""
        self._draw_rounded_rect(
            left,
            top,
            right,
            bottom,
            radius=18,
            fill=self.colors["card_bg"],
            outline=self.colors["sidebar_border"],
            width=1,
        )

        self.canvas.create_text(
            left + 28,
            top + 34,
            text=icon,
            anchor=tk.CENTER,
            font=("Segoe UI", 17, "bold"),
            fill=self.colors["accent"],
        )

        self.canvas.create_text(
            left + 64,
            top + 34,
            text=title,
            anchor="w",
            font=("Segoe UI", 15, "bold"),
            fill=self.colors["text_primary"],
        )

    def _draw_legend(self, x_pos: float, y_pos: float) -> None:
        """Draw the visual legend for zone and drone statuses."""
        items = [
            ("Start", self.colors["zone_start"], "circle"),
            ("Restricted", self.colors["zone_restricted"], "circle"),
            ("End", self.colors["zone_end"], "circle"),
            ("Priority", self.colors["zone_priority"], "circle"),
            ("Normal", self.colors["zone_normal"], "circle"),
            ("Blocked", self.colors["zone_blocked"], "circle"),
            ("Drone", self.colors["drone_waiting"], "agent"),
        ]

        col_gap = max((self._inner_right - self._inner_left) * 0.45, 172)
        row_h = 25

        for index, (label, color, marker_type) in enumerate(items):
            row = index // 2
            col = index % 2

            cx = x_pos + col * col_gap
            cy = y_pos + row * row_h

            if marker_type == "agent":
                self.canvas.create_oval(
                    cx,
                    cy - 6,
                    cx + 12,
                    cy + 6,
                    fill=color,
                    outline="#F8FAFC",
                    width=1,
                )
            else:
                self.canvas.create_oval(
                    cx,
                    cy - 6,
                    cx + 12,
                    cy + 6,
                    fill=color,
                    outline="#111827",
                    width=1,
                )

            self.canvas.create_text(
                cx + 24,
                cy,
                text=label,
                anchor="w",
                font=("Segoe UI", 10),
                fill=self.colors["text_secondary"],
            )

    def _draw_controls(
        self,
        on_back: Callable[[], None],
        on_next: Callable[[], None],
        on_play: Callable[[], None],
        on_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_exit: Callable[[], None],
        card_top: float,
        card_bottom: float,
    ) -> None:
        """Draw playback, navigation, reset, and exit controls."""
        host_left = self._inner_left + 34
        host_top = card_top + 56
        host_width = self._inner_right - self._inner_left - 68
        host_height = max(card_bottom - host_top - 24, 104)

        if self.controls_frame is not None:
            self.controls_frame.destroy()

        self.controls_frame = ttk.Frame(self.window, style="Sidebar.TFrame")

        for col in range(3):
            self.controls_frame.columnconfigure(col, weight=1, uniform="ctrl")
        for row in range(2):
            self.controls_frame.rowconfigure(row, weight=1, uniform="ctrl")

        buttons = [
            ("←", on_back, "Control.TButton", 0, 0),
            ("→", on_next, "Control.TButton", 0, 1),
            ("▶", on_play, "Play.TButton", 0, 2),
            ("Ⅱ", on_pause, "Control.TButton", 1, 0),
            ("↻", on_reset, "Control.TButton", 1, 1),
            ("↪", on_exit, "Danger.TButton", 1, 2),
        ]

        for text, command, style, row, col in buttons:
            ttk.Button(
                self.controls_frame,
                text=text,
                style=style,
                command=command,
            ).grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        self.canvas.create_window(
            host_left,
            host_top,
            anchor="nw",
            window=self.controls_frame,
            width=host_width,
            height=host_height,
        )

    def _draw_rounded_rect(
        self,
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
        """Draw a rounded rectangle and return its canvas item id."""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]

        return self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=width,
            tags=() if tags is None else tags,
        )
