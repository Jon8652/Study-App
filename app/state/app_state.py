"""Application state + use-case layer (Part D).

AppState is the single coordinator between the GUI, core engines, and the
persistence repository. Screens never touch raw session storage or file I/O
directly; they call action methods and read derived views.

Includes an in-memory daily index (Part L) rebuilt on load and updated
incrementally on add/delete so calendar/stats stay responsive with 10k+
sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from app.core.date_rules import sessions_for_day
from app.core.medals import DayAggregate, build_day_aggregates
from app.core.models import Dataset, Session, Settings
from app.core.stats import StatsResult, compute_stats
from app.persistence import repository
from app.persistence.schema import SaveError


@dataclass
class ActionResult:
    """Uniform friendly result for GUI-facing operations."""

    ok: bool
    message: str | None = None      # friendly error/notice when relevant
    value: object | None = None     # payload such as created session


class AppState:
    """Central mutable application state with derived caches."""

    def __init__(self, dataset: Dataset | None = None):
        self.dataset: Dataset = dataset or Dataset.empty()
        self._day_index: dict[date, DayAggregate] = {}
        self._listeners: list[Callable[[], None]] = []
        self.dirty: bool = False
        self.rebuild_index()

    # -- listener / refresh plumbing ------------------------------------------

    def add_listener(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in self._listeners:
            try:
                callback()
            except Exception:
                # A broken listener must not corrupt app state (ERR-17).
                pass

    # -- persistence ------------------------------------------------------------

    def load_startup(self) -> repository.LoadOutcome:
        """Run the startup load flow and adopt the resulting dataset."""
        outcome = repository.load_startup()
        self.dataset = outcome.dataset
        self.dirty = False
        self.rebuild_index()
        return outcome

    def autosave(self) -> ActionResult:
        """Save current state to the default save file (FR-57).

        On disk failure, in-memory data remains usable (ERR-13).
        """
        try:
            repository.save_dataset(self.dataset)
            self.dirty = False
            return ActionResult(ok=True)
        except SaveError as exc:
            return ActionResult(ok=False, message=str(exc))

    def manual_save(self) -> ActionResult:
        """Manual Save from Settings — writes immediately (FR-59)."""
        result = self.autosave()
        if result.ok:
            self._notify()
        return result

    def prepare_manual_load(self, path: Path) -> ActionResult:
        """Validate a selected file WITHOUT changing current state (FR-61)."""
        try:
            dataset, warnings = repository.validate_file_for_manual_load(path)
        except SaveError as exc:
            return ActionResult(ok=False, message=str(exc))
        return ActionResult(ok=True, value=dataset,
                            message=warnings[0] if warnings else None)

    def commit_manual_load(self, dataset: Dataset) -> ActionResult:
        """Replace in-memory data after confirmation (FR-62/A-9/FR-65)."""
        try:
            repository.apply_manual_load(dataset)
        except SaveError as exc:
            return ActionResult(ok=False, message=str(exc))
        self.dataset = dataset
        self.dirty = False
        self.rebuild_index()
        self._notify()
        return ActionResult(ok=True)

    # -- settings ----------------------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self.dataset.settings

    def set_theme(self, theme: str) -> ActionResult:
        if theme not in ("dark", "light"):
            return ActionResult(ok=False, message="Unknown theme selected.")
        self.dataset.settings.theme = theme
        self._mark_dirty_and_save()
        self._notify()
        return ActionResult(ok=True)

    # -- session mutations ---------------------------------------------------------

    def log_preset_session(self, duration_minutes: int,
                           source: str = "preset") -> ActionResult:
        """Log a preset one-tap session (FR-1)."""
        return self._log_session(duration_minutes, source)

    def log_custom_session(self, hours, minutes) -> ActionResult:
        """Validate + log a custom session (FR-2..FR-5)."""
        total, error = Session.validate_custom_inputs(hours, minutes)
        if error is not None:
            return ActionResult(ok=False, message=error)
        return self._log_session(total, "custom")

    def _log_session(self, duration_minutes: int, source: str) -> ActionResult:
        error = Session.validate_duration(duration_minutes)
        if error is not None:
            return ActionResult(ok=False, message=error)
        session = Session.create(duration_minutes=duration_minutes, source=source)
        self.dataset.sessions.append(session)
        self._index_add(session)
        self._mark_dirty_and_save()
        self._notify()
        return ActionResult(ok=True, value=session)

    def delete_session(self, session_id: str) -> ActionResult:
        """Delete a session and update every derived view (FR-13..FR-15)."""
        session = self.dataset.session_by_id(session_id)
        if session is None:
            return ActionResult(ok=False,
                                message="That session could not be found.")
        self.dataset.sessions.remove(session)
        self._index_remove(session)
        self._mark_dirty_and_save()
        self._notify()
        return ActionResult(ok=True)

    def _mark_dirty_and_save(self) -> None:
        self.dirty = True
        # Autosave after any data-changing action (FR-57).
        self.autosave()

    # -- daily index (Part L optimization) --------------------------------------

    def rebuild_index(self) -> None:
        """Rebuild the day-aggregate index from all sessions."""
        self._day_index = build_day_aggregates(
            self.dataset.sessions, self.dataset.settings.xp_per_10_minutes
        )

    def _index_add(self, session: Session) -> None:
        day = session.day
        rate = self.dataset.settings.xp_per_10_minutes
        xp = (session.duration_minutes // 10) * rate
        existing = self._day_index.get(day)
        if existing is None:
            from app.core.medals import medal_for_minutes

            self._day_index[day] = DayAggregate(
                day=day,
                total_minutes=session.duration_minutes,
                total_xp=xp,
                medal=medal_for_minutes(session.duration_minutes),
                session_ids=(session.id,),
            )
        else:
            from dataclasses import replace as dc_replace

            from app.core.medals import medal_for_minutes

            total_minutes = existing.total_minutes + session.duration_minutes
            self._day_index[day] = dc_replace(
                existing,
                total_minutes=total_minutes,
                total_xp=existing.total_xp + xp,
                medal=medal_for_minutes(total_minutes),
                session_ids=existing.session_ids + (session.id,),
            )

    def _index_remove(self, session: Session) -> None:
        day = session.day
        existing = self._day_index.get(day)
        if existing is None:
            return
        from dataclasses import replace as dc_replace

        from app.core.medals import medal_for_minutes

        remaining_ids = tuple(sid for sid in existing.session_ids
                              if sid != session.id)
        if not remaining_ids:
            del self._day_index[day]
            return
        rate = self.dataset.settings.xp_per_10_minutes
        total_minutes = existing.total_minutes - session.duration_minutes
        # XP must be recomputed from the *remaining* sessions: partial
        # 10-minute blocks make XP non-additive, so simple subtraction of
        # the removed session's XP would be wrong (e.g. days of 10+10+5).
        remaining = [
            s for s in self.dataset.sessions
            if s.day == day and s.id != session.id
        ]
        total_xp = sum((s.duration_minutes // 10) * rate for s in remaining)
        self._day_index[day] = dc_replace(
            existing,
            total_minutes=total_minutes,
            total_xp=total_xp,
            medal=medal_for_minutes(total_minutes),
            session_ids=remaining_ids,
        )

    # -- derived views --------------------------------------------------------------

    def get_day_aggregate(self, day: date) -> DayAggregate | None:
        return self._day_index.get(day)

    def get_today_summary(self) -> DayAggregate | None:
        return self._day_index.get(date.today())

    def get_month_view_data(self, year: int, month: int) -> dict[date, DayAggregate]:
        """Return indexed aggregates for days in the given month."""
        return {
            day: agg
            for day, agg in self._day_index.items()
            if day.year == year and day.month == month
        }

    def get_day_details(self, day: date) -> dict:
        """Everything the day-details dialog needs, freshly derived."""
        sessions = sessions_for_day(self.dataset.sessions, day)
        aggregate = self._day_index.get(day)
        return {
            "day": day,
            "sessions": sessions,
            "total_minutes": aggregate.total_minutes if aggregate else 0,
            "total_xp": aggregate.total_xp if aggregate else 0,
            "medal": aggregate.medal if aggregate else None,
        }

    def get_stats(self) -> StatsResult:
        return compute_stats(
            self.dataset.sessions, self.dataset.settings, today=date.today()
        )
