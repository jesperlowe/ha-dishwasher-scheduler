from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Callable, Mapping, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHEAPEST_HOUR_ENTITY,
    CONF_READY_SUBSTRING,
    CONF_PLANNING_MODE,
    CONF_DOOR_SENSOR,
    CONF_POWER_SWITCH,
    CONF_DEFAULT_DURATION_MINUTES,
    CONF_PROGRAM_SELECT_ENTITY,
    CONF_START_BUTTON_ENTITY,
    CONF_STATUS_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_PLANNING_MODE,
    DEFAULT_READY_SUBSTRING,
    DEFAULT_DURATION_MINUTES,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    INTEGRATION_VERSION,
    MODE_CHEAPEST_24H,
    MODE_START_NOW,
    SERVICE_SCHEDULE_FROM_PRICES,
)

CallbackType = Callable[[], None]

_LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeState:
    """Runtime data for the scheduler."""

    armed: bool = False
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    planned_duration_minutes: int = DEFAULT_DURATION_MINUTES
    last_attempt: Optional[datetime] = None
    last_result: str = "never"
    started_at: Optional[datetime] = None


class DishwasherSchedulerCoordinator:
    """Central coordinator handling scheduling and triggers."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.unsub_timer: Optional[Callable[[], None]] = None
        self.unsub_door: Optional[Callable[[], None]] = None
        self.state = RuntimeState()
        self._listeners: list[CallbackType] = []
        _LOGGER.debug("Coordinator created for entry %s", entry.entry_id)

    @property
    def cheapest_hour_entity(self) -> str:
        return self.entry.data[CONF_CHEAPEST_HOUR_ENTITY]

    @property
    def status_entity(self) -> str:
        return self.entry.data[CONF_STATUS_ENTITY]

    @property
    def start_button_entity(self) -> str:
        return self.entry.data[CONF_START_BUTTON_ENTITY]

    @property
    def program_select_entity(self) -> Optional[str]:
        return self.entry.data.get(CONF_PROGRAM_SELECT_ENTITY)

    @property
    def door_sensor(self) -> Optional[str]:
        return self._opt(CONF_DOOR_SENSOR, None)

    @property
    def power_switch(self) -> Optional[str]:
        return self._opt(CONF_POWER_SWITCH, None)

    @property
    def default_duration_minutes(self) -> int:
        try:
            return int(self._opt(CONF_DEFAULT_DURATION_MINUTES, DEFAULT_DURATION_MINUTES))
        except (TypeError, ValueError):
            return DEFAULT_DURATION_MINUTES

    def _opt(self, key: str, default):
        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _parse_time(self, key: str, default_value: str) -> time:
        raw_value = self._opt(key, default_value)

        if isinstance(raw_value, time):
            return raw_value

        if isinstance(raw_value, str):
            parsed = dt_util.parse_time(raw_value)
            if parsed:
                return parsed

        try:
            hour = int(float(raw_value))
            return time(hour % 24, 0)
        except (TypeError, ValueError):
            return dt_util.parse_time(default_value) or time(0, 0)

    def _window_minutes(self, key: str, default_value: str) -> int:
        parsed_time = self._parse_time(key, default_value)
        return parsed_time.hour * 60 + parsed_time.minute

    async def async_update_option(self, key: str, value: Any) -> None:
        """Persist an option update and refresh planning."""

        options = {**self.entry.options, key: value}
        await self.hass.config_entries.async_update_entry(
            self.entry, options=options
        )

        if key in {
            CONF_WINDOW_START,
            CONF_WINDOW_END,
            CONF_PLANNING_MODE,
            CONF_DEFAULT_DURATION_MINUTES,
        }:
            self._recompute_planned_start()

        self._notify_listeners()

    @property
    def ready_substring(self) -> str:
        return self._opt(CONF_READY_SUBSTRING, DEFAULT_READY_SUBSTRING)

    @property
    def window_start(self) -> time:
        return self._parse_time(CONF_WINDOW_START, DEFAULT_WINDOW_START)

    @property
    def window_end(self) -> time:
        return self._parse_time(CONF_WINDOW_END, DEFAULT_WINDOW_END)

    @property
    def planning_mode(self) -> str:
        return self._opt(CONF_PLANNING_MODE, DEFAULT_PLANNING_MODE)

    async def async_start(self) -> None:
        """Begin listening for ticks and compute initial plan."""
        self._recompute_planned_start()
        self.unsub_timer = async_track_time_change(
            self.hass, self._handle_minute_tick, second=0
        )
        if self.door_sensor:
            self.unsub_door = async_track_state_change_event(
                self.hass, [self.door_sensor], self._handle_door_event
            )
        _LOGGER.info(
            "Dishwasher Scheduler %s started for entry %s",
            INTEGRATION_VERSION,
            self.entry.entry_id,
        )
        self._notify_listeners()

    async def async_stop(self) -> None:
        """Stop scheduler callbacks."""
        if self.unsub_timer:
            self.unsub_timer()
            self.unsub_timer = None
            _LOGGER.debug("Stopped scheduler timer for %s", self.entry.entry_id)
        if self.unsub_door:
            self.unsub_door()
            self.unsub_door = None
            _LOGGER.debug("Stopped door listener for %s", self.entry.entry_id)

    def set_armed(self, value: bool) -> None:
        """Arm or disarm the scheduler."""
        self.state.armed = value
        _LOGGER.info("Scheduler %s set to armed=%s", self.entry.entry_id, value)
        if value:
            self._recompute_planned_start()
        self._notify_listeners()

    def set_planned_start(self, planned: Optional[datetime]) -> None:
        """Set a planned start time and notify listeners."""
        self.state.planned_start = planned
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
            _LOGGER.warning("Cheapest hour entity %s not found", self.cheapest_hour_entity)
            return None

        state_value = st.state
        if isinstance(state_value, str):
            state_value = state_value.strip()

        try:
            hour = int(float(state_value))
        except (ValueError, TypeError):
            parsed_time = dt_util.parse_time(state_value)
            if parsed_time:
                hour = parsed_time.hour
            else:
                parsed_datetime = dt_util.parse_datetime(state_value)
                if parsed_datetime:
                    hour = dt_util.as_local(parsed_datetime).hour
                else:
                    _LOGGER.error("Invalid cheapest hour state: %s", st.state)
                    return None
        if 0 <= hour <= 23:
            return hour
        _LOGGER.error("Cheapest hour out of range: %s", st.state)
        return None

    def _within_window(self, target) -> bool:
        start = self._window_minutes(CONF_WINDOW_START, DEFAULT_WINDOW_START)
        end = self._window_minutes(CONF_WINDOW_END, DEFAULT_WINDOW_END)

        if isinstance(target, datetime):
            local_dt = dt_util.as_local(target)
            target_minutes = local_dt.hour * 60 + local_dt.minute
        elif isinstance(target, time):
            target_minutes = target.hour * 60 + target.minute
        else:
            try:
                target_minutes = int(float(target)) * 60
            except (TypeError, ValueError):
                return False

        if start == end:
            return True
        if start < end:
            return start <= target_minutes < end
        return (target_minutes >= start) or (target_minutes < end)

    def _within_window_span(self, start_dt: datetime, duration_minutes: int) -> bool:
        """Check whether a start/end span fits within the configured window."""

        if duration_minutes <= 0:
            return False

        start_minutes = self._window_minutes(CONF_WINDOW_START, DEFAULT_WINDOW_START)
        end_minutes = self._window_minutes(CONF_WINDOW_END, DEFAULT_WINDOW_END)

        local_start = dt_util.as_local(start_dt)
        local_end = local_start + timedelta(minutes=duration_minutes)

        start_minute_of_day = local_start.hour * 60 + local_start.minute
        end_minute_of_day = local_end.hour * 60 + local_end.minute

        if start_minutes == end_minutes:
            return True

        if start_minutes < end_minutes:
            if local_end.date() != local_start.date():
                return False
            return (
                start_minute_of_day >= start_minutes
                and end_minute_of_day <= end_minutes
            )

        # Window wraps over midnight
        if start_minute_of_day >= start_minutes:
            # Starting late evening; must finish before window end next day
            return (
                local_end.date() > local_start.date()
                and end_minute_of_day <= end_minutes
            )

        # Starting after midnight; ensure finish before end_minutes same day
        return end_minute_of_day <= end_minutes

    def _recompute_planned_start(self) -> None:
        mode = self.planning_mode
        now = dt_util.now()

        if mode == MODE_START_NOW:
            candidate = (now + timedelta(minutes=1)).replace(
                second=0, microsecond=0
            )
            self.state.planned_start = candidate
            self.state.planned_duration_minutes = self.default_duration_minutes
            self.state.planned_end = candidate + timedelta(
                minutes=self.state.planned_duration_minutes
            )
            _LOGGER.info("Planning mode is start now; planned start %s", candidate)
            return

        cheapest = self._get_cheapest_hour()
        if cheapest is None:
            self.state.planned_start = None
            _LOGGER.info("No valid cheapest hour available; clearing planned start")
            return

        candidate = now.replace(minute=0, second=0, microsecond=0, hour=cheapest)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)

        if not self._within_window_span(candidate, self.default_duration_minutes):
            self.state.planned_start = None
            self.state.planned_end = None
            _LOGGER.info(
                "Cheapest hour %s outside allowed window %s-%s",
                cheapest,
                self.window_start,
                self.window_end,
            )
            return

        self.state.planned_start = candidate
        self.state.planned_duration_minutes = self.default_duration_minutes
        self.state.planned_end = candidate + timedelta(
            minutes=self.state.planned_duration_minutes
        )
        _LOGGER.info(
            "Planned start recalculated: %s (duration %s minutes)",
            candidate,
            self.state.planned_duration_minutes,
        )

    def _status_is_ready(self) -> bool:
        st = self.hass.states.get(self.status_entity)
        if st is None:
            _LOGGER.warning("Status entity %s not found", self.status_entity)
            return False
        state = (st.state or "").strip()
        if state.lower() in {"unknown", "unavailable", ""}:
            _LOGGER.debug("Status entity %s is unavailable", self.status_entity)
            return False
        return self.ready_substring.lower() in state.lower()

    async def _press_start_button(self) -> None:
        await self.hass.services.async_call(
            "button", "press", {"entity_id": self.start_button_entity}, blocking=True
        )

    async def _ensure_power_on(self) -> None:
        if not self.power_switch:
            return
        state = self.hass.states.get(self.power_switch)
        if state and state.state.lower() == "on":
            return

        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self.power_switch}, blocking=True
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
        _LOGGER.debug("Attempting to start dishwasher at %s", now)

        if self.state.planned_end and not self._within_window_span(
            planned, self.state.planned_duration_minutes
        ):
            self.state.last_result = "outside_window"
            self.state.armed = False
            _LOGGER.warning("Planned start no longer within allowed window; cancelling")
            self._notify_listeners()
            return

        if not self._status_is_ready():
            self.state.last_result = "not_ready"
            _LOGGER.warning("Dishwasher not ready at planned start time")
            self._notify_listeners()
            return

        try:
            await self._ensure_power_on()
            await self._press_start_button()
            self.state.last_result = "started"
            self.state.armed = False
            self.state.started_at = now
            _LOGGER.info("Dishwasher start command sent successfully")
        except Exception:  # noqa: BLE001
            self.state.last_result = "start_failed"
            _LOGGER.exception("Failed to start dishwasher")
        finally:
            self._notify_listeners()

    def _get_program_half_hours(
        self,
        default_half_hours: int,
        program_durations: Optional[Mapping[str, int]] = None,
    ) -> int:
        """Return duration in half hours based on the current program selection."""

        if not program_durations or not self.program_select_entity:
            return default_half_hours

        state = self.hass.states.get(self.program_select_entity)
        if state is None:
            _LOGGER.warning(
                "Program select entity %s not found", self.program_select_entity
            )
            return default_half_hours

        program = state.state
        if program in program_durations and program_durations[program] > 0:
            return int(program_durations[program])

        _LOGGER.info(
            "No program duration mapping found for %s; using default %s half-hours",
            program,
            default_half_hours,
        )
        return default_half_hours

    def _get_price_slots(self, price_entity: str):
        st = self.hass.states.get(price_entity)
        if st is None:
            _LOGGER.warning("Price entity %s not found", price_entity)
            return []

        slots = []
        for key in ("raw_today", "raw_tomorrow"):
            raw = st.attributes.get(key)
            if not isinstance(raw, list):
                continue

            for item in raw:
                start_str = item.get("start") or item.get("hour")
                value = item.get("value")
                if value is None:
                    value = item.get("price")
                if start_str is None or value is None:
                    continue

                start = dt_util.parse_datetime(start_str)
                if start is None:
                    continue

                try:
                    price_value = float(value)
                except (TypeError, ValueError):
                    continue

                slots.append((dt_util.as_utc(start), price_value))

        slots.sort(key=lambda slot: slot[0])
        now = dt_util.utcnow()
        return [slot for slot in slots if slot[0] >= now]

    def _find_cheapest_window(
        self, price_entity: str, duration_half_hours: int
    ) -> Optional[datetime]:
        slots = self._get_price_slots(price_entity)
        if not slots:
            _LOGGER.warning("No price slots available from %s", price_entity)
            return None

        needed_slots = duration_half_hours * 2
        if len(slots) < needed_slots:
            _LOGGER.warning(
                "Not enough price slots (%s available) for %s half-hours",
                len(slots),
                duration_half_hours,
            )
            return None

        best_total = None
        best_start = None
        duration_minutes = duration_half_hours * 30

        for idx in range(len(slots) - needed_slots + 1):
            window = slots[idx : idx + needed_slots]
            start_dt = window[0][0]
            if not self._within_window_span(start_dt, duration_minutes):
                continue

            total_price = sum(value for _, value in window)
            if best_total is None or total_price < best_total:
                best_total = total_price
                best_start = start_dt

        if best_start:
            _LOGGER.info(
                "Cheapest %s half-hour window starts at %s with total %.3f",
                duration_half_hours,
                best_start,
                best_total,
            )
        else:
            _LOGGER.info(
                "No valid window found inside the allowed hours (%s-%s)",
                self.window_start,
                self.window_end,
            )
        return best_start

    async def async_schedule_from_prices(
        self,
        price_entity: str,
        duration_half_hours: int,
        program_durations: Optional[Mapping[str, int]] = None,
        arm: bool = True,
    ) -> None:
        duration = max(1, duration_half_hours)
        resolved_duration = self._get_program_half_hours(duration, program_durations)
        best_start = self._find_cheapest_window(price_entity, resolved_duration)

        if best_start is None:
            self.state.planned_start = None
            self.state.planned_end = None
            self._notify_listeners()
            return

        self.state.planned_start = best_start
        self.state.planned_duration_minutes = resolved_duration * 30
        self.state.planned_end = best_start + timedelta(
            minutes=self.state.planned_duration_minutes
        )
        if arm:
            self.state.armed = True
        self._notify_listeners()

    async def _handle_door_event(self, event) -> None:
        if not self.state.started_at:
            return

        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state.lower() != "on":
            return

        self.state.armed = False
        self.state.planned_start = None
        self.state.planned_end = None
        self.state.started_at = None
        self.state.last_result = "reset_on_door_open"
        _LOGGER.info("Dishwasher cycle complete; schedule reset after door opened")
        self._notify_listeners()
