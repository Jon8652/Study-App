"""Centralized asset loading helper (Part J).

All GUI code loads images through this module so asset path logic is never
duplicated across UI files. Missing assets must never crash the app; callers
receive ``None`` and fall back to text labels (FR-79, ERR-12).
"""

from __future__ import annotations

from pathlib import Path

from app.utils.paths import get_asset_path

# Cache loaded images so tkinter references stay alive (prevents GC issues)
_IMAGE_CACHE: dict[str, object] = {}

ASSET_FILENAMES = {
    "app_icon": "app_icon.png",
    "home_icon": "home_icon.png",
    "calendar_icon": "calendar_icon.png",
    "stats_icon": "stats_icon.png",
    "settings_icon": "settings_icon.png",
    "bronze_medal": "bronze_medal.png",
    "silver_medal": "silver_medal.png",
    "gold_medal": "gold_medal.png",
    "empty_state": "empty_state.png",
}


def asset_exists(key: str) -> bool:
    """Return True if the asset file for ``key`` exists on disk."""
    filename = ASSET_FILENAMES.get(key)
    if filename is None:
        return False
    return get_asset_path(filename).is_file()


def load_photo(key: str, size: int | None = None):
    """Load an asset as a tkinter-compatible PhotoImage, or return None.

    Uses Pillow when available for scaling; falls back gracefully when the
    asset file is missing or cannot be decoded. The returned image object is
    cached so it stays referenced for the lifetime of the process.

    Returns an object usable by both tkinter and customtkinter widgets, or
    ``None`` when unavailable (callers must then use a text fallback).
    """
    filename = ASSET_FILENAMES.get(key)
    if filename is None:
        return None

    cache_name = key if size is None else f"{key}@{size}"
    if cache_name in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_name]

    path: Path = get_asset_path(filename)
    if not path.is_file():
        return None

    try:
        from PIL import Image, ImageTk

        with Image.open(path) as img:
            img = img.convert("RGBA")
            if size is not None:
                img = img.resize((size, size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
    except Exception:
        try:
            # Plain tkinter PNG support (Tk >= 8.6) without Pillow
            import tkinter as tk

            photo = tk.PhotoImage(file=str(path))
            if size is not None:
                factor = max(1, round(photo.width() / max(size, 1)))
                if factor > 1:
                    photo = photo.subsample(factor, factor)
        except Exception:
            return None

    _IMAGE_CACHE[cache_name] = photo
    return photo
