"""Main application window (Part E).

Owns navigation, screen switching, theme application, startup load flow,
and graceful shutdown. Screens are created once and cached; the visible one
is raised on nav clicks. AppState listeners refresh all screens after any
data change so views stay consistent everywhere (FR-26 / Risk 4).
"""

from __future__ import annotations

import customtkinter as ctk

from app.constants import (
    APP_NAME,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from app.gui.dialogs.message_dialog import show_message
from app.gui.screens.calendar_screen import CalendarScreen
from app.gui.screens.home_screen import HomeScreen
from app.gui.screens.notes_screen import NotesScreen
from app.gui.screens.settings_screen import SettingsScreen
from app.gui.screens.stats_screen import StatsScreen
from app.persistence.schema import FRIENDLY_MESSAGES, FutureSchemaError
from app.state.app_state import AppState
from app.utils.paths import get_default_save_path
from app.utils.resources import load_photo

NAV_ITEMS = (
    ("home", "Home", "home_icon"),
    ("calendar", "Calendar", "calendar_icon"),
    ("notes", "Notes", "notes_icon"),
    ("stats", "Statistics", "stats_icon"),
    ("settings", "Settings", "settings_icon"),
)

NAV_ICONS_LIGHT = ("gray20", "gray85")  # text color tuple for inactive buttons


class MainWindow(ctk.CTk):
    # NOTE: `state` is a reserved Tkinter attribute (window deiconify/iconic
    # status, used by customtkinter's DPI-scaling tracker). The app state must
    # never be assigned to that name on a Tk widget — use `_app_state`.
    def __init__(self, app_state: AppState | None = None):
        super().__init__()
        ctk.set_appearance_mode("dark")  # A-10: dark default before load
        ctk.set_default_color_theme("blue")

        self._app_state = app_state or AppState()

        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        icon = load_photo("app_icon", size=64)
        if icon is not None:
            try:
                # CTkImage exposes the underlying PIL image; tkinter needs a
                # PhotoImage for iconphoto. Keep a reference so it survives GC.
                # Import the Tkinter compat modules explicitly: PyInstaller's
                # analysis sometimes misses these lazy Pillow imports, which
                # makes PhotoImage raise in frozen builds.
                from PIL import ImageTk
                import PIL.ImageDraw  # noqa: F401  (ImageTk dependency)

                try:
                    import PIL._imagingtk  # noqa: F401
                    import PIL._tkinter_finder  # noqa: F401
                except ImportError:
                    pass

                self._icon_ref = ImageTk.PhotoImage(icon.pil_image)
                self.iconphoto(True, self._icon_ref)
            except Exception:
                pass  # window icon is best-effort (ERR-12)

        # --- layout: sidebar + content ---------------------------------------
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=180)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        brand = ctk.CTkLabel(
            self.sidebar, text=APP_NAME,
            font=ctk.CTkFont(size=15, weight="bold"), wraplength=160,
        )
        brand.pack(pady=(20, 18), padx=10)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_icon_refs: dict[str, object] = {}
        for key, label, icon_key in NAV_ITEMS:
            button = ctk.CTkButton(
                self.sidebar, text=f"  {label}", height=40, anchor="w",
                fg_color="transparent", hover_color=("gray75", "gray25"),
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self.show_screen(k),
            )
            # Part J task 3: nav icons when the asset is available; the text
            # label always remains, so missing icons never break navigation.
            icon = load_photo(icon_key, size=18)
            if icon is not None:
                self._nav_icon_refs[key] = icon
                button.configure(image=icon)
            button.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = button

        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # --- screens (created once, cached) ------------------------------------
        self.screens: dict[str, object] = {}
        self.screens["home"] = HomeScreen(self.content_area, self._app_state)
        self.screens["calendar"] = CalendarScreen(self.content_area, self._app_state)
        self.screens["notes"] = NotesScreen(self.content_area, self._app_state)
        self.screens["stats"] = StatsScreen(self.content_area, self._app_state)
        self.screens["settings"] = SettingsScreen(
            self.content_area, self._app_state, on_theme_change=self.apply_theme
        )
        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")

        # Any data change refreshes every screen at once.
        self._app_state.add_listener(self.refresh_all)

        self.current_screen_key: str | None = None
        self.show_screen("home")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------------

    def show_screen(self, key: str) -> None:
        self.current_screen_key = key
        screen = self.screens[key]
        screen.tkraise()
        for other_key, button in self._nav_buttons.items():
            button.configure(
                fg_color="gray25" if other_key == key else "transparent",
                text_color="white" if other_key == key else ("gray20", "gray85"),
            )

    def refresh_all(self) -> None:
        for screen in self.screens.values():
            try:
                screen.refresh()
            except Exception:
                pass  # a broken refresh must never crash the app (ERR-17)

    def apply_theme(self, theme: str) -> None:
        mode = {"dark": "dark", "light": "light"}.get(theme, "dark")
        ctk.set_appearance_mode(mode)

    # --- startup / shutdown ---------------------------------------------------

    def run_startup_load(self) -> None:
        """Execute the persistence startup flow with friendly notices.

        - Normal load / first-run creation: silent.
        - Recovered from backup or started empty: friendly message.
        - Future schema version: warn and refuse to modify the file (FR-72).
        """
        try:
            outcome = self._app_state.load_startup()
        except FutureSchemaError:
            self._app_state.dataset = type(self._app_state.dataset).empty()
            self._app_state.rebuild_index()
            self.after(200, lambda: show_message(
                self, "Newer data file", FRIENDLY_MESSAGES["future_schema"]))
            return
        except Exception:
            # Absolute last resort: keep the app usable with empty data.
            self.after(200, lambda: show_message(
                self, "Heads up", FRIENDLY_MESSAGES["started_empty"]))
            return

        self.apply_theme(self._app_state.settings.theme)
        self.refresh_all()

        if outcome.notice:
            title = ("Data recovered" if outcome.recovered_from_backup
                     else "Heads up")
            self.after(200, lambda: show_message(self, title, outcome.notice))

    def _on_close(self) -> None:
        """Flush unsaved changes before exiting (FR-58), then quit."""
        if self._app_state.dirty:
            result = self._app_state.autosave()
            if not result.ok:
                show_message(self, "Couldn't save", result.message or "")
        self.destroy()
