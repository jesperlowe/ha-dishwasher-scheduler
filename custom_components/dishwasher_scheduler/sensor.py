from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    INTEGRATION_VERSION,
    SENSOR_LAST_ATTEMPT,
    SENSOR_LAST_RESULT,
    SENSOR_PLANNED_START,
)
from .coordinator import DishwasherSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for Dishwasher Scheduler."""
    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PlannedStartSensor(coordinator),
            LastAttemptSensor(coordinator),
            LastResultSensor(coordinator),
        ],
        update_before_add=True,
    )


class BaseDishwasherSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: DishwasherSchedulerCoordinator, name: str, unique: str):
        self.coordinator = coordinator
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{unique}"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Dishwasher Scheduler",
            manufacturer="Custom",
            model="Scheduler",
            sw_version=INTEGRATION_VERSION,
        )


class PlannedStartSensor(BaseDishwasherSensor):
    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        super().__init__(
            coordinator,
            "Planned start",
            SENSOR_PLANNED_START,
        )

    @property
    def native_value(self):
        dt_value = self.coordinator.state.planned_start
        if dt_value is None:
            return None
        return dt_util.as_local(dt_value).isoformat(timespec="minutes")


class LastAttemptSensor(BaseDishwasherSensor):
    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        super().__init__(
            coordinator,
            "Last attempt",
            SENSOR_LAST_ATTEMPT,
        )

    @property
    def native_value(self):
        dt_value = self.coordinator.state.last_attempt
        if dt_value is None:
            return None
        return dt_util.as_local(dt_value).isoformat(timespec="minutes")


class LastResultSensor(BaseDishwasherSensor):
    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        super().__init__(
            coordinator,
            "Last result",
            SENSOR_LAST_RESULT,
        )

    @property
    def native_value(self):
        return self.coordinator.state.last_result
