"""Base class for primary screens (Parts E-H).

Every screen gets a title area, a content frame, and a ``refresh()`` hook
that AppState listeners call after any data change.
"""

from __future__ import annotations

import customtkinter as ctk

from app.state.app_state import AppState


class BaseScreen(ctk.CTkFrame):
    def __init__(self, master, state: AppState, title: str = ""):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.state = state
        self._title_text = title

        self.title_label = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=22, weight="bold"), anchor="w"
        )
        if title:
            self.title_label.pack(fill="x", pady=(6, 10), padx=4)

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Re-pull derived data from AppState and update widgets."""
        raise NotImplementedError

    # Friendly empty-state helper shared by all screens (Part E/K).
    def show_empty_state(self, parent, message: str):
        label = ctk.CTkLabel(
            parent,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray65"),
            justify="center",
            wraplength=420,
        )
        return label
