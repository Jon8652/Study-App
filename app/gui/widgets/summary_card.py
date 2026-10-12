"""Reusable summary card widget (Parts F/H).

A rounded frame containing a big value and an optional caption — used for
the Today card on Home and every stat tile on the Stats screen.
"""

from __future__ import annotations

import customtkinter as ctk


class SummaryCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "\u2014",
                 caption: str | None = None, width: int = 180, **kwargs):
        super().__init__(master, corner_radius=12, width=width, **kwargs)
        self._title = title
        self.value_label = ctk.CTkLabel(
            self, text=value, font=ctk.CTkFont(size=24, weight="bold")
        )
        self.value_label.pack(pady=(14, 2))
        self.caption_label = ctk.CTkLabel(
            self, text=caption or title,
            font=ctk.CTkFont(size=12), text_color=("gray35", "gray70"),
        )
        self.caption_label.pack(pady=(0, 12))

    def set_value(self, value: str, caption: str | None = None) -> None:
        self.value_label.configure(text=value)
        if caption is not None:
            self.caption_label.configure(text=caption)
