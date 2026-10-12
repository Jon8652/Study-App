"""Calendar screen (Part G).

Month grid with medal indicators, prev/next/today navigation, and a modal
day-details dialog on day click. Initial view is the current month; the last
viewed month is preserved while the app runs.

Days that have notes show a small note-count marker in the cell, and the
notes themselves are listed inside the day-details dialog.
"""

from __future__ import annotations

import calendar as pycal
from datetime import date

import customtkinter as ctk

from app.gui.dialogs.day_details_dialog import DayDetailsDialog
from app.gui.screens.base_screen import BaseScreen
from app.utils.date_utils import add_months, format_minutes

WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

NOTE_MARKER = "\U0001F4DD"  # memo emoji shown when a day has notes

MEDAL_FG = {
    "bronze": "#8a5a33",
    "silver": "#7d8894",
    "gold":   "#a6821f",
}


class CalendarScreen(BaseScreen):
    def __init__(self, master, state):
        super().__init__(master, state, title="Calendar")

        today = date.today()
        self._year, self._month = today.year, today.month
        self._selected: date | None = None  # selected on first visit below

        # --- header row: < Month Year > [Today] ------------------------------
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(header, text="\u2039", width=40, height=32,
                      command=self._prev_month).pack(side="left")
        self.month_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=17, weight="bold"), width=190
        )
        self.month_label.pack(side="left", padx=8)
        ctk.CTkButton(header, text="\u203a", width=40, height=32,
                      command=self._next_month).pack(side="left")
        ctk.CTkButton(header, text="Today", width=80, height=32, fg_color="gray30",
                      hover_color="gray25", command=self._go_today).pack(side="right")

        # --- grid ------------------------------------------------------------
        self.grid_frame = ctk.CTkFrame(self.content, corner_radius=12)
        self.grid_frame.pack(fill="both", expand=True)

        for col, label in enumerate(WEEKDAY_LABELS):
            ctk.CTkLabel(
                self.grid_frame, text=label, font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray35", "gray70"),
            ).grid(row=0, column=col, sticky="nsew", padx=2, pady=(10, 4))

        self._cells: dict[date, ctk.CTkButton] = {}
        self._render()

    # --- navigation -----------------------------------------------------------

    def _prev_month(self) -> None:
        anchor = date(self._year, self._month, 1)
        shifted = add_months(anchor, -1)
        self._year, self._month = shifted.year, shifted.month
        self._render()

    def _next_month(self) -> None:
        anchor = date(self._year, self._month, 1)
        shifted = add_months(anchor, 1)
        self._year, self._month = shifted.year, shifted.month
        self._render()

    def _go_today(self) -> None:
        today = date.today()
        self._year, self._month = today.year, today.month
        self._selected = today
        self._render()

    # --- rendering --------------------------------------------------------------

    def _render(self) -> None:
        for child in self.grid_frame.winfo_children():
            if getattr(child, "_is_day_cell", False):
                child.destroy()
        self._cells.clear()

        month_name = pycal.month_name[self._month]
        self.month_label.configure(text=f"{month_name} {self._year}")

        aggregates = self.state.get_month_view_data(self._year, self._month)
        note_counts = self.state.get_note_counts_by_day()
        today = date.today()

        # Monday-first week layout (calendar.setfirstweekday safe locally).
        cal = pycal.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self._year, self._month)

        for week_index, week_days in enumerate(weeks, start=1):
            for col, day_num in enumerate(week_days):
                if day_num == 0:
                    continue
                day = date(self._year, self._month, day_num)
                aggregate = aggregates.get(day)

                text = str(day_num)
                if aggregate:
                    text += f"\n{format_minutes(aggregate.total_minutes)}"
                    if aggregate.medal:
                        text = f"{aggregate.medal[0].upper()} \u00b7 {text}"

                notes_count = note_counts.get(day, 0)
                if notes_count:
                    marker = f"{NOTE_MARKER}{notes_count}" if notes_count > 1 \
                        else NOTE_MARKER
                    text += f"\n{marker}"

                fg = MEDAL_FG.get(aggregate.medal) if aggregate else None
                if fg is None and day == today:
                    fg = "#3a6ea5"

                cell = ctk.CTkButton(
                    self.grid_frame,
                    text=text,
                    font=ctk.CTkFont(size=12),
                    height=58,
                    corner_radius=8,
                    fg_color=fg or "gray18",
                    hover_color=fg or "gray25",
                    text_color="white",
                    command=lambda d=day: self._open_day(d),
                )
                cell._is_day_cell = True
                cell.grid(row=week_index, column=col, sticky="nsew", padx=2, pady=2)
                self._cells[day] = cell

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1)
        for row in range(1, len(weeks) + 1):
            self.grid_frame.grid_rowconfigure(row, weight=1)

    def _open_day(self, day: date) -> None:
        self._selected = day
        DayDetailsDialog(self.winfo_toplevel(), self.state, day)

    def refresh(self) -> None:
        """Called by AppState listeners after any data change."""
        self._render()
