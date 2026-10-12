"""Notes screen.

View, write, edit, and delete titled notes. Each note is stored separately
with its own title inside the dataset (so it persists through the normal
autosave/backup flow) and may be attached to a calendar day — attached
notes also appear on that day in the Calendar and in the day-details
dialog.

Layout: list of notes on the left (with search + New note button), full
text of the selected note on the right with Edit / Delete actions.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from app.core.models import Note
from app.gui.dialogs.confirm_dialog import ask_yes_no
from app.gui.dialogs.message_dialog import show_error
from app.gui.dialogs.note_editor_dialog import NoteEditorDialog
from app.gui.screens.base_screen import BaseScreen
from app.utils.date_utils import format_date_long


class NotesScreen(BaseScreen):
    def __init__(self, master, state):
        super().__init__(master, state, title="Notes")

        self._selected_note_id: str | None = None
        self._note_rows: dict[str, ctk.CTkButton] = {}

        # --- toolbar -----------------------------------------------------------
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            toolbar, text="+  New note", width=130,
            command=self._new_note,
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="Search notes…", width=240,
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        # --- body: list + detail pane ---------------------------------------
        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(
            body, label_text="All notes", corner_radius=12,
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.detail_frame = ctk.CTkFrame(body, corner_radius=12)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self.detail_frame.grid_columnconfigure(0, weight=1)
        self.detail_frame.grid_rowconfigure(1, weight=1)

        self.detail_title = ctk.CTkLabel(
            self.detail_frame, text="",
            font=ctk.CTkFont(size=17, weight="bold"), anchor="w", wraplength=460,
        )
        self.detail_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))

        self.detail_subtitle = ctk.CTkLabel(
            self.detail_frame, text="",
            font=ctk.CTkFont(size=12), anchor="w", justify="left",
            text_color=("gray40", "gray65"), wraplength=460,
        )
        self.detail_subtitle.grid(row=0, column=0, sticky="ew",
                                  padx=16, pady=(0, 6))

        self.detail_body = ctk.CTkTextbox(
            self.detail_frame, font=ctk.CTkFont(size=13), wrap="word",
            activate_scrollbars=True,
        )
        self.detail_body.grid(row=1, column=0, sticky="nsew", padx=16)
        self.detail_body.configure(state="disabled")

        actions = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 14))
        self.edit_button = ctk.CTkButton(actions, text="Edit note", width=110,
                                         command=self._edit_selected)
        self.edit_button.pack(side="left", padx=(0, 8))
        self.delete_button = ctk.CTkButton(
            actions, text="Delete", width=90, fg_color="#8b3030",
            hover_color="#a33d3d", command=self._delete_selected)
        self.delete_button.pack(side="left")
        self.open_day_button = ctk.CTkButton(
            actions, text="Open day", width=100, fg_color="gray30",
            hover_color="gray25", command=self._open_day_of_selected)

        self.detail_empty = self.show_empty_state(
            self.detail_frame,
            "Select a note on the left, or create one with “New note”.\n"
            "Notes attached to a day also show up on that day in the Calendar.",
        )

        self.refresh()

    # --- actions ---------------------------------------------------------------

    def _new_note(self, day: date | None = None) -> None:
        NoteEditorDialog(self.winfo_toplevel(), self.state, note=None,
                         default_day=day)

    def _edit_selected(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        NoteEditorDialog(self.winfo_toplevel(), self.state, note=note)

    def _delete_selected(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        confirmed = ask_yes_no(
            self.winfo_toplevel(),
            "Delete note?",
            f"Delete “{note.display_title()}” permanently?\n\n"
            "This cannot be undone.",
            confirm_text="Delete",
            cancel_text="Keep it",
        )
        if not confirmed:
            return
        result = self.state.delete_note(note.id)
        if not result.ok:
            show_error(self, result.message or "That note could not be found.")

    def _open_day_of_selected(self) -> None:
        note = self._selected_note()
        if note is not None and note.day is not None:
            from app.gui.dialogs.day_details_dialog import DayDetailsDialog

            DayDetailsDialog(self.winfo_toplevel(), self.state, note.day)

    def _selected_note(self) -> Note | None:
        if self._selected_note_id is None:
            return None
        return self.state.dataset.note_by_id(self._selected_note_id)

    def _select(self, note_id: str) -> None:
        self._selected_note_id = note_id
        self._render_list()
        self._render_detail()

    # --- rendering -------------------------------------------------------------

    def refresh(self) -> None:
        """Called by AppState listeners after any data change."""
        notes = self.state.get_all_notes()
        if self._selected_note_id is not None and \
                not any(n.id == self._selected_note_id for n in notes):
            self._selected_note_id = notes[0].id if notes else None
        elif self._selected_note_id is None and notes:
            self._selected_note_id = notes[0].id
        self._render_list()
        self._render_detail()

    def _filtered_notes(self) -> list[Note]:
        notes = self.state.get_all_notes()
        try:
            query = self.search_entry.get().strip().lower()
        except Exception:
            query = ""
        if not query:
            return notes
        return [
            n for n in notes
            if query in n.display_title().lower() or query in n.body.lower()
        ]

    def _render_list(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._note_rows.clear()

        notes = self._filtered_notes()
        if not notes:
            ctk.CTkLabel(
                self.list_frame,
                text="No notes yet." if not self.state.dataset.notes
                     else "No notes match your search.",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "gray65"),
            ).pack(pady=18, padx=12)
            return

        for note in notes:
            day_tag = f" · {note.day.strftime('%b %d')}" if note.day else ""
            preview = note.body.strip().replace("\n", " ")
            if len(preview) > 60:
                preview = preview[:57] + "…"
            text = f"{note.display_title()}{day_tag}"
            if preview:
                text += f"\n{preview}"
            selected = note.id == self._selected_note_id
            row = ctk.CTkButton(
                self.list_frame, text=text, anchor="w",
                justify="left", height=54, corner_radius=8,
                fg_color="gray25" if selected else "gray18",
                hover_color="gray25",
                font=ctk.CTkFont(size=13),
                command=lambda nid=note.id: self._select(nid),
            )
            row.pack(fill="x", padx=6, pady=3)
            self._note_rows[note.id] = row

    def _render_detail(self) -> None:
        note = self._selected_note()
        if note is None:
            self.detail_title.grid_forget()
            self.detail_subtitle.grid_forget()
            self.detail_body.grid_forget()
            self.detail_empty.grid_forget()
            self.detail_empty.place(relx=0.5, rely=0.5, anchor="center")
            self.edit_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
            self.open_day_button.grid_forget()
            return

        self.detail_empty.place_forget()
        self.detail_empty.grid_forget()
        self.detail_title.grid(row=0, column=0, sticky="ew",
                               padx=16, pady=(14, 2))
        self.detail_body.grid(row=1, column=0, sticky="nsew", padx=16)

        subtitle_parts = []
        if note.day is not None:
            subtitle_parts.append(format_date_long(note.day))
        subtitle_parts.append(f"Updated {note.updated_at_local:%Y-%m-%d %H:%M}")
        self.detail_subtitle.grid(row=0, column=0, sticky="ew",
                                  padx=16, pady=(0, 6))
        self.detail_title.configure(text=note.display_title())
        self.detail_subtitle.configure(text="   ·   ".join(subtitle_parts))

        self.detail_body.configure(state="normal")
        self.detail_body.delete("1.0", "end")
        self.detail_body.insert("1.0", note.body if note.body.strip()
                                else "(no text)")
        self.detail_body.configure(state="disabled")

        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        if note.day is not None:
            self.open_day_button.grid(side="left", padx=(16, 0))
            self.open_day_button.configure(state="normal")
        else:
            self.open_day_button.grid_forget()
