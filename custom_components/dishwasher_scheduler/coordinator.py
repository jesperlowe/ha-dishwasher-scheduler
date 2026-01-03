from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHEAPEST_HOUR_ENTITY,
    CONF_READY_SUBSTRING,
    CONF_START_BUTTON_ENTITY,
    CONF_STATUS_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_READY_SUBSTRING,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
)

CallbackType = Callable[[], None]


@dataclass
class RuntimeState:
    """Runtime data for the scheduler."""

    armed: bool = False
    planned_start: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    last_result: str = "never"


class DishwasherSchedulerCoordinator:
    """Central coordinator handling scheduling and triggers."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.unsub_timer: Optional[Callable[[], None]] = None
        self.state = RuntimeState()
        self._listeners: list[CallbackType] = []

    @property
    def cheapest_hour_entity(self) -> str:
        return self.entry.data[CONF_CHEAPEST_HOUR_ENTITY]

    @property
    def status_entity(self) -> str:
        return self.entry.data[CONF_STATUS_ENTITY]

    @property
    def start_button_entity(self) -> str:
        return self.entry.data[CONF_START_BUTTON_ENTITY]

    def _opt(self, key: str, default):
        return self.entry.options.get(key, self.entry.data.get(key, default))

    @property
    def ready_substring(self) -> str:
        return self._opt(CONF_READY_SUBSTRING, DEFAULT_READY_SUBSTRING)

    @property
    def window_start(self) -> int:
        return int(self._opt(CONF_WINDOW_START, DEFAULT_WINDOW_START))

    @property
    def window_end(self) -> int:
        return int(self._opt(CONF_WINDOW_END, DEFAULT_WINDOW_END))

    async def async_start(self) -> None:
        """Begin listening for ticks and compute initial plan."""
        self._recompute_planned_start()
        self.unsub_timer = async_track_time_change(
            self.hass, self._handle_minute_tick, second=0
        )
        self._notify_listeners()

    async def async_stop(self) -> None:
        """Stop scheduler callbacks."""
        if self.unsub_timer:
            self.unsub_timer()
            self.unsub_timer = None

    def set_armed(self, value: bool) -> None:
        """Arm or disarm the scheduler."""
        self.state.armed = value
        if value:
            self._recompute_planned_start()
        self._notify_listeners()

    def async_add_listener(self, listener: CallbackType) -> CallbackType:
        """Register a state listener and return unsubscribe callback."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _get_cheapest_hour(self) -> Optional[int]:
        st = self.hass.states.get(self.cheapest_hour_entity)
        if st is None:
            return None
        try:
            hour = int(float(st.state))
        except (ValueError, TypeError):
            return None
        if 0 <= hour <= 23:
            return hour
        return None

    def _within_window(self, hour: int) -> bool:
        start = self.window_start
        end = self.window_end
        if start == end:
            return True
        if start < end:
            return start <= hour < end
        return (hour >= start) or (hour < end)

    def _recompute_planned_start(self) -> None:
        cheapest = self._get_cheapest_hour()
        if cheapest is None:
            self.state.planned_start = None
            return

        now = dt_util.now()
        candidate = now.replace(minute=0, second=0, microsecond=0, hour=cheapest)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)

        if not self._within_window(cheapest):
            self.state.planned_start = None
            return

        self.state.planned_start = candidate

    def _status_is_ready(self) -> bool:
        st = self.hass.states.get(self.status_entity)
        if st is None:
            return False
        state = (st.state or "").strip()
        if state.lower() in {"unknown", "unavailable", ""}:
            return False
        return self.ready_substring.lower() in state.lower()

    async def _press_start_button(self) -> None:
        await self.hass.services.async_call(
            "button", "press", {"entity_id": self.start_button_entity}, blocking=True
        )

    async def _handle_minute_tick(self, now: datetime) -> None:
        if self.state.planned_start is None and self.state.armed:
            self._recompute_planned_start()

        planned = self.state.planned_start
        if not self.state.armed or planned is None:
            self._notify_listeners()
            return

        if now.strftime("%Y-%m-%d %H:%M") != planned.strftime("%Y-%m-%d %H:%M"):
            self._notify_listeners()
            return

        self.state.last_attempt = now

        if not self._status_is_ready():
            self.state.last_result = "not_ready"
            self._notify_listeners()
            return

        try:
            await self._press_start_button()
            self.state.last_result = "started"
            self.state.armed = False
        except Exception:  # noqa: BLE001
            self.state.last_result = "start_failed"
        finally:
            self._notify_listeners()
