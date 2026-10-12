"""Session row widget for the day-details dialog (Part G).

Displays start time, end time, duration, source, and a delete action.
The caller supplies ``on_delete`` which must confirm before deleting
(FR-13..FR-15 / ERR-5).
"""

from __future__ import annotations

import customtkinter as ctk

from app.core.models import Session
from app.utils.date_utils import format_minutes, format_time


class SessionRow(ctk.CTkFrame):
    def __init__(self, master, session: Session, xp_rate: int,
                 on_delete=None, **kwargs):
        super().__init__(master, corner_radius=8, **kwargs)

        info = (
            f"{format_time(session.start_local)} \u2192 {format_time(session.end_local)}   "
            f"\u00b7   {format_minutes(session.duration_minutes)}   "
            f"\u00b7   {(session.duration_minutes // 10) * xp_rate} XP"
            f"   \u00b7   {session.source}"
        )
        ctk.CTkLabel(
            self, text=info, font=ctk.CTkFont(size=13), anchor="w"
        ).pack(side="left", padx=(14, 6), pady=10)

        if on_delete is not None:
            ctk.CTkButton(
                self,
                text="Delete",
                width=76,
                height=26,
                fg_color="#8b3030",
                hover_color="#a33d3d",
                command=lambda: on_delete(session),
            ).pack(side="right", padx=(6, 12), pady=8)
