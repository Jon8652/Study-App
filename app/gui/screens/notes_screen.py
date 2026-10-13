"""Notes screen.

View, write, edit, and delete titled notes. Each note is stored separately
with its own title inside the dataset (so it persists through the normal
autosave/backup flow) and may be attached to a calendar day — attached
notes also appear on that day in the Calendar and in the day-details
dialog.

Layout: list of notes on the left (with search + New note button), full
text of the selected note on the right with Edit / Delete actions; the
note's day and "Updated …" timestamp appear at the bottom-right of the
detail pane, next to the Delete button.
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from app.core.models import Note
from app.gui.dialogs.confirm_dialog import ask_yes_no
from app.gui.dialogs.message_dialog import show_error
from app.gui.dialogs.note_editor_dialog import NoteEditorDialog
from app.gui.screens.base_screen import BaseScreen
from app.gui.theme import (
    ACCENT,
    BORDER,
    CARD_FG,
    MUTED_TEXT,
    danger_button,
    neutral_button,
)
from app.utils.date_utils import format_date_long

# Note-row fills: selected rows get a tinted accent background in dark mode
# and a soft blue in light mode, so selection reads clearly in both themes.
NOTE_ROW_SELECTED = ("#dbe7f5", "#2b3a52")
NOTE_ROW_HOVER = ("#eef1f5", "#31313d")


class NotesScreen(BaseScreen):
    def __init__(self, master, state):
        super().__init__(master, state, title="Notes")

        self._selected_note_id: str | None = None
        # NOTE: we intentionally do NOT keep references to the per-note row
        # buttons. customtkinter's CTkButton can raise AttributeError in
        # destroy() (missing '_font' attribute) on some versions when a
        # partially-constructed button is torn down; holding refs doesn't
        # help and stale refs cause "dead widget" errors after refresh().
        # Rows are recreated from scratch on every render instead.

        # --- toolbar -----------------------------------------------------------
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            toolbar, text="+  New note", width=130, height=34,
            corner_radius=8, command=self._new_note,
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="\U0001F50D  Search notes…", width=240,
            height=34, corner_radius=8,
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
            fg_color=CARD_FG, border_width=1, border_color=BORDER,
            label_font=ctk.CTkFont(size=13, weight="bold"),
            # Left-align the "All notes" header (the default is centered).
            label_anchor="w",
        )
        # The scroll frame's header is a CTkLabel created with
        # corner_radius = frame corner_radius (12), which gives it customtkinter's
        # hidden internal text inset of min(corner_radius, height/2) = 6 px —
        # that pushed "All notes" 6 px right of the note rows.  Zero it so the
        # header text starts at exactly the same x as the row buttons below.
        for _child in self.list_frame._parent_frame.winfo_children():
            if isinstance(_child, ctk.CTkLabel):
                _child.configure(corner_radius=0)
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.detail_frame = ctk.CTkFrame(
            body, corner_radius=12, fg_color=CARD_FG,
            border_width=1, border_color=BORDER)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self.detail_frame.grid_columnconfigure(0, weight=1)
        self.detail_frame.grid_rowconfigure(1, weight=1)

        # CTkLabel indents its inner text by min(corner_radius, height/2);
        # corner_radius=0 keeps the title at exactly the grid padx edge.
        self.detail_title = ctk.CTkLabel(
            self.detail_frame, text="",
            font=ctk.CTkFont(size=17, weight="bold"), anchor="w", wraplength=460,
            corner_radius=0,
        )
        self.detail_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        self.detail_body = ctk.CTkTextbox(
            self.detail_frame, font=ctk.CTkFont(size=13), wrap="word",
            activate_scrollbars=True, corner_radius=8,
            border_width=1, border_color=BORDER,
        )
        # The textbox insets its text internally by max(corner_radius,
        # border_width + 1) = 8 px, so use a smaller outer padx (16 - 8 = 8)
        # to keep the body text on the same left edge as the title above.
        self.detail_body.grid(row=1, column=0, sticky="nsew", padx=8)
        self.detail_body.configure(state="disabled")

        actions = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 14))
        self.edit_button = ctk.CTkButton(actions, text="Edit note", width=110,
                                         height=32, corner_radius=8,
                                         command=self._edit_selected)
        # Buttons are solid filled controls: their *background* (not the
        # inset text) should start at the card's 16 px content edge, like
        # the "+ New note" button in the toolbar above.
        self.edit_button.pack(side="left", padx=(0, 8))
        self.delete_button = danger_button(
            actions, text="Delete", width=90, height=32,
            command=self._delete_selected)
        self.delete_button.pack(side="left")
        self.open_day_button = neutral_button(
            actions, text="Open day", width=100, height=32,
            command=self._open_day_of_selected)
        # Date / "Updated …" info sits at the bottom-right of the action
        # row (next to Delete) instead of under the title, where it used to
        # collide with long wrapped titles.
        self.detail_meta = ctk.CTkLabel(
            actions, text="",
            font=ctk.CTkFont(size=12), anchor="e", justify="right",
            text_color=MUTED_TEXT,
        )
        self.detail_meta.pack(side="right")

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

    def _clear_children(self, frame) -> None:
        """Safely destroy every child of *frame*.

        customtkinter widgets can raise AttributeError inside ``destroy()``
        (e.g. "'CTkButton' object has no attribute '_font'" on some ctk
        versions when a widget was only partially constructed).  That used
        to abort the whole refresh, leaving stale rows behind and making
        search/delete/new notes appear broken.  Swallow per-widget teardown
        errors so the list is always rebuilt correctly; also forget any
        tkinter-level children first so they stop receiving events even if
        their Python-side destroy fails.
        """
        for child in frame.winfo_children():
            try:
                child.forget()
            except Exception:
                pass
            try:
                child.destroy()
            except Exception:
                pass

    def _render_list(self) -> None:
        self._clear_children(self.list_frame)

        notes = self._filtered_notes()
        if not notes:
            # corner_radius=0 cancels CTkLabel's hidden internal text inset
            # (min(corner_radius, height/2) = 6 px by default); with padx=12
            # the text then starts at the same x as the note-row text.
            ctk.CTkLabel(
                self.list_frame,
                text="No notes yet." if not self.state.dataset.notes
                     else "No notes match your search.",
                font=ctk.CTkFont(size=13),
                text_color=MUTED_TEXT,
                anchor="w", corner_radius=0,
            ).pack(fill="x", pady=18, padx=(15, 6))
            return

        for note in notes:
            selected = note.id == self._selected_note_id

            day_tag = note.day.strftime("%b %d") if note.day else ""
            preview = note.body.strip().replace("\n", " ")
            if len(preview) > 60:
                preview = preview[:57] + "…"

            row = ctk.CTkFrame(
                self.list_frame, corner_radius=8,
                fg_color=NOTE_ROW_SELECTED if selected else CARD_FG,
                border_width=1,
                border_color=ACCENT if selected else BORDER,
            )
            # Title / date / preview are each their own plain CTkLabel with
            # anchor="w" and justify="left".  A single multi-line CTkButton
            # (as used previously) cannot do per-line left justification:
            # customtkinter never forwards `justify` to the button's inner
            # tkinter label, so short lines such as calendar notes' date tag
            # rendered centred inside the label's bounding box — and every
            # calendar-attached note (title, date and content alike) looked
            # centre-aligned compared to regular notes.
            labels = [(note.display_title(),
                       ctk.CTkFont(size=13, weight="bold"),
                       ACCENT if selected else None)]
            if day_tag:
                labels.append((day_tag, ctk.CTkFont(size=12), MUTED_TEXT))
            if preview:
                labels.append((preview, ctk.CTkFont(size=12), MUTED_TEXT))
            for i, (txt, fnt, color) in enumerate(labels):
                # corner_radius=0 cancels CTkLabel's hidden internal text
                # inset of min(corner_radius, height/2); the default theme
                # gives labels corner_radius=6, which used to shift every
                # line a few px right of where it was packed.
                ctk.CTkLabel(
                    row, text=txt, font=fnt, anchor="w", justify="left",
                    corner_radius=0,
                    text_color=color if color is not None else ("gray90", "gray10"),
                ).pack(fill="x", padx=4,
                       pady=((8, 2) if i == 0 else (0, 8) if i == len(labels) - 1 else 0))

            # The old (correctly aligned) rows were CTkButtons whose text
            # landed at canvas-inset + 15 (pack padx 6 + border 1 + the
            # button's own max(corner_radius, border+1) = 8 px gutter).
            # pack padx=(9, 6) + frame border 1 + label padx 4 reproduces
            # that exact left edge for every line of every row.
            row.pack(fill="x", padx=(9, 6), pady=3)
            # Make the whole card clickable like the old button rows.
            row.bind("<Button-1>", lambda _e, nid=note.id: self._select(nid))
            for child in row.winfo_children():
                child.bind("<Button-1>",
                           lambda _e, nid=note.id: self._select(nid))

    def _render_detail(self) -> None:
        note = self._selected_note()
        if note is None:
            self.detail_title.grid_forget()
            self.detail_body.grid_forget()
            self.detail_empty.grid_forget()
            self.detail_empty.place(relx=0.5, rely=0.5, anchor="center")
            self.edit_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
            self.open_day_button.pack_forget()
            self.detail_meta.pack_forget()
            return

        self.detail_empty.place_forget()
        self.detail_empty.grid_forget()
        self.detail_title.grid(row=0, column=0, sticky="ew",
                               padx=16, pady=(14, 6))
        # padx=8 matches the textbox's internal 8 px text inset so the body
        # text starts on the same left edge as the title (see __init__).
        self.detail_body.grid(row=1, column=0, sticky="nsew", padx=8)

        meta_parts = []
        if note.day is not None:
            meta_parts.append(format_date_long(note.day))
        meta_parts.append(
            f"Updated {note.updated_at_local:%Y-%m-%d %H:%M}")
        self.detail_meta.pack(side="right")
        self.detail_meta.configure(text="   ·   ".join(meta_parts))
        self.detail_title.configure(text=note.display_title())

        self.detail_body.configure(state="normal")
        self.detail_body.delete("1.0", "end")
        self.detail_body.insert("1.0", note.body if note.body.strip()
                                else "(no text)")
        self.detail_body.configure(state="disabled")

        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        if note.day is not None:
            # NOTE: `side` is a pack option, not a grid option — passing it
            # to grid() raised TclError ("bad option -side") and broke note
            # selection. The button lives inside the packed `actions` frame,
            # so pack it like its siblings.
            self.open_day_button.pack(side="left")
            self.open_day_button.configure(state="normal")
        else:
            self.open_day_button.pack_forget()
