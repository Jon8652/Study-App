"""Centralised visual theme tokens for the Study Tracker UI.

Every colour used by the GUI lives here so screens/dialogs/widgets stay
visually consistent across light *and* dark mode.  Previously several
buttons were hard-coded to ``gray30``/``gray25`` pairs, which are nearly
invisible on a light-mode background; the neutral tokens below are proper
(light, dark) tuples resolved by customtkinter per appearance mode.

Colour conventions
------------------
- ACCENT      – primary blue used for main actions, active nav pills,
                today's calendar tile and the "Today" header button.
- NEUTRAL     – quieter secondary actions (Cancel / Close / Open day …).
- DANGER      – destructive actions (Delete session / Delete note).
- CARD_FG / BORDER – elevated panel look: subtle border around every card
                so panels read as distinct surfaces on both themes.
"""

from __future__ import annotations

import customtkinter as ctk

# --- Accent ------------------------------------------------------------------
ACCENT = "#2b6cb0"            # blue, identical in light + dark modes
ACCENT_HOVER = "#255a94"
ACCENT_TEXT = "white"

# Secondary accents used for coloured stat values on the Home screen.
TIME_BLUE = ("#22589d", "#6ea8e0")
XP_GOLD = ("#a6821f", "#d4af37")

# --- Neutral / semantic buttons ----------------------------------------------
# NOTE: customtkinter accepts either a plain colour string or a *flat* tuple of
# exactly two strings – one per appearance mode (light, dark).  Nesting pairs
# inside the tuple (e.g. (("a","b"),("c","d"))) raises ValueError at widget
# construction time.
NEUTRAL = ("#dfe4ea", "gray28")
NEUTRAL_HOVER = ("#d3d9e0", "gray35")
NEUTRAL_TEXT = ("gray10", "gray92")
DANGER = ("#8b3030", "#b04040")
DANGER_HOVER = ("#a33d3d", "#c44e4e")

# --- Surfaces ------------------------------------------------------------------
CARD_FG = ("#fbfcfd", "#242430")   # CTk default-ish panel colours
BORDER = ("#dde2e8", "#3f3f50")    # subtle outline that separates cards
NAV_ACTIVE_BG = ("#dbe7f5", "#2b6cb0")
NAV_HOVER = ("#edf1f5", "#33333d")
SIDEBAR_FG = ("#f2f4f8", "#1d1d28")
MUTED_TEXT = ("gray40", "gray65")


def card(master=None, corner_radius: int = 14, **kwargs):
    """Return a themed CTkFrame styled as an elevated card."""
    return ctk.CTkFrame(
        master,
        corner_radius=corner_radius,
        fg_color=CARD_FG,
        border_width=1,
        border_color=BORDER,
        **kwargs,
    )


def neutral_button(master=None, text: str = "", width: int = 100,
                   height: int = 28, command=None, **kwargs):
    """A quiet secondary action button (Cancel / Close / Open day …)."""
    return ctk.CTkButton(
        master,
        text=text,
        width=width,
        height=height,
        fg_color=NEUTRAL,
        hover_color=NEUTRAL_HOVER,
        text_color=NEUTRAL_TEXT,
        command=command,
        **kwargs,
    )


def danger_button(master=None, text: str = "Delete", width: int = 90,
                  height: int = 28, command=None, **kwargs):
    """A red destructive-action button."""
    return ctk.CTkButton(
        master,
        text=text,
        width=width,
        height=height,
        fg_color=DANGER,
        hover_color=DANGER_HOVER,
        text_color="white",
        command=command,
        **kwargs,
    )
