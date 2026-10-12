"""Day-details modal dialog (Part G).

Shows the selected date, total study time, XP, medal, and the session list
with per-session delete buttons. Deletion requires confirmation; after any
delete the dialog refreshes itself and AppState notifies all screens so
calendar/home/stats update immediately (FR-15).
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from app.core.medals import medal_label
from app.gui.dialogs.confirm_dialog import ask_yes_no
from app.gui.widgets.medal_badge import MedalBadge
from app.gui.widgets.session_row import SessionRow
from app.state.app_state import AppState
from app.utils.date_utils import format_date_long, format_minutes


class DayDetailsDialog(ctk.CTkToplevel):
    def __init__(self, master, state: AppState, day: date):
        super().__init__(master)
        self._state = state
        self._day = day

        self.title("Day details")
        self.transient(master)
        self.geometry("560x480")
        self.minsize(460, 380)

        container = ctk.CTkFrame(self, corner_radius=0)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        self.header_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.header_label.pack(pady=(10, 2))

        totals_row = ctk.CTkFrame(container, fg_color="transparent")
        totals_row.pack(pady=(2, 8))
        self.totals_label = ctk.CTkLabel(totals_row, text="", font=ctk.CTkFont(size=13))
        self.totals_label.pack(side="left", padx=(0, 12))
        self.medal_badge = MedalBadge(totals_row, None, size=22)
        self.medal_badge.pack(side="left")
        self.medal_text_label = ctk.CTkLabel(totals_row, text="", font=ctk.CTkFont(size=13))
        self.medal_text_label.pack(side="left", padx=(4, 0))

        self.list_frame = ctk.CTkScrollableFrame(container, label_text="Sessions")
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self.empty_label = ctk.CTkLabel(
            container,
            text="No study sessions were logged on this day yet.\n"
                 "Time logged today will appear here.",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
            justify="center",
        )

        ctk.CTkButton(container, text="Close", width=100, fg_color="gray30",
                      hover_color="gray25", command=self.destroy).pack(pady=(0, 10))

        self.grab_set()
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the dialog contents from freshly derived state."""
        details = self._state.get_day_details(self._day)
        sessions = details["sessions"]

        self.header_label.configure(text=format_date_long(self._day))
        self.totals_label.configure(
            text=f"{format_minutes(details['total_minutes'])}   \u00b7   "
                 f"{details['total_xp']} XP"
        )
        medal = details["medal"]
        self.medal_badge.set_medal(medal)
        self.medal_text_label.configure(
            text=f"Medal: {medal_label(medal)}" if medal else "No medal yet"
        )

        for child in self.list_frame.winfo_children():
            child.destroy()

        if not sessions:
            self.empty_label.pack(pady=(0, 10))
            return
        self.empty_label.pack_forget()

        xp_rate = self._state.settings.xp_per_10_minutes
        for session in sessions:
            SessionRow(
                self.list_frame, session, xp_rate,
                on_delete=self._confirm_delete,
            ).pack(fill="x", padx=4, pady=3)

    def _confirm_delete(self, session) -> None:
        confirmed = ask_yes_no(
            self,
            "Delete session?",
            f"Delete this {format_minutes(session.duration_minutes)} session "
            f"({session.start_local.strftime('%H:%M')} - "
            f"{session.end_local.strftime('%H:%M')})?\n\n"
            "Medals, streaks, and stats will update right away.",
            confirm_text="Delete",
            cancel_text="Keep it",
        )
        if not confirmed:
            return
        result = self._state.delete_session(session.id)
        if not result.ok:
            from app.gui.dialogs.message_dialog import show_error

            show_error(self, result.message or "That session could not be found.")
            return
        # AppState._notify() refreshes calendar/home/stats; refresh ourselves too.
        self.refresh()
