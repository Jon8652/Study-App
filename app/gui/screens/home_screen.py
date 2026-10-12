"""Home / Log Study screen (Part F).

- Today summary card: total study time, XP earned, current medal status.
- One-tap preset buttons: 30 minutes / 1 hour / 2 hours (FR-1).
- Custom session modal (FR-2..FR-5) with friendly validation.
- Summary refreshes immediately after any successful log (listener-driven).
"""

from __future__ import annotations

import customtkinter as ctk

from app.constants import PRESET_DURATIONS_MINUTES, PRESET_LABELS
from app.core.medals import medal_label
from app.gui.dialogs.custom_session_dialog import CustomSessionDialog
from app.gui.dialogs.message_dialog import show_error
from app.gui.screens.base_screen import BaseScreen
from app.gui.widgets.medal_badge import MedalBadge
from app.utils.date_utils import format_minutes


class HomeScreen(BaseScreen):
    def __init__(self, master, state):
        super().__init__(master, state, title="Log Study")

        # --- Today summary panel -------------------------------------------
        card = ctk.CTkFrame(self.content, corner_radius=14)
        card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            card, text="Today", font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        ).pack(fill="x", padx=18, pady=(14, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))

        self.time_value = ctk.CTkLabel(
            row, text="0m", font=ctk.CTkFont(size=28, weight="bold")
        )
        self.time_value.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text="study time", font=ctk.CTkFont(size=12),
                     text_color=("gray35", "gray70")).grid(row=1, column=0, sticky="w")

        self.xp_value = ctk.CTkLabel(
            row, text="0 XP", font=ctk.CTkFont(size=28, weight="bold")
        )
        self.xp_value.grid(row=0, column=1, padx=(48, 0), sticky="e")
        ctk.CTkLabel(row, text="XP earned", font=ctk.CTkFont(size=12),
                     text_color=("gray35", "gray70")).grid(row=1, column=1, sticky="e")

        medal_row = ctk.CTkFrame(card, fg_color="transparent")
        medal_row.pack(fill="x", padx=18, pady=(0, 14))
        self.medal_badge = MedalBadge(medal_row, None, size=22)
        self.medal_badge.pack(side="left")
        self.medal_label = ctk.CTkLabel(
            medal_row, text="No medal yet today", font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
        )
        self.medal_label.pack(side="left", padx=(6, 0))

        # --- Preset buttons ---------------------------------------------------
        ctk.CTkLabel(
            self.content, text="Quick log", font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        presets = ctk.CTkFrame(self.content, fg_color="transparent")
        presets.pack(fill="x", pady=(0, 10))
        for i, minutes in enumerate(PRESET_DURATIONS_MINUTES):
            ctk.CTkButton(
                presets,
                text=PRESET_LABELS.get(minutes, f"{minutes} minutes"),
                height=52,
                font=ctk.CTkFont(size=15, weight="bold"),
                command=lambda m=minutes: self._log_preset(m),
            ).grid(row=0, column=i, padx=(0, 10), sticky="ew")
            presets.grid_columnconfigure(i, weight=1)

        ctk.CTkButton(
            self.content,
            text="+ Log custom session",
            height=44,
            fg_color="gray30",
            hover_color="gray25",
            command=self._open_custom_dialog,
        ).pack(fill="x", pady=(2, 0))

        self.empty_hint = ctk.CTkLabel(
            self.content,
            text="Nothing logged today yet. Tap a button above to log your "
                 "first study session!",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
            wraplength=520,
            justify="left",
        )

        self.refresh()

    # ------------------------------------------------------------------------

    def _log_preset(self, minutes: int) -> None:
        result = self.state.log_preset_session(minutes, source="preset")
        if not result.ok:
            show_error(self, result.message or "Could not log that session.")

    def _open_custom_dialog(self) -> None:
        CustomSessionDialog(self.winfo_toplevel(), self._log_custom)

    def _log_custom(self, total_minutes: int) -> None:
        result = self.state.log_custom_session(
            total_minutes // 60, total_minutes % 60
        )
        if not result.ok:
            show_error(self, result.message or "Could not log that session.")

    def refresh(self) -> None:
        aggregate = self.state.get_today_summary()
        minutes = aggregate.total_minutes if aggregate else 0
        xp = aggregate.total_xp if aggregate else 0
        medal = aggregate.medal if aggregate else None

        self.time_value.configure(text=format_minutes(minutes))
        self.xp_value.configure(text=f"{xp} XP")

        self.medal_badge.set_medal(medal)
        if medal:
            self.medal_label.configure(text=f"{medal_label(medal)} medal earned today!")
        elif minutes >= 120:  # unreachable, but keeps logic simple
            self.medal_label.configure(text="")
        else:
            to_bronze = max(0, 120 - minutes)
            if minutes == 0:
                self.medal_label.configure(text="No medal yet today")
            else:
                self.medal_label.configure(
                    text=f"{format_minutes(to_bronze)} more for Bronze today"
                )

        if minutes == 0:
            self.empty_hint.pack(fill="x", pady=(12, 0))
        else:
            self.empty_hint.pack_forget()
