from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEFAULT_DURATION_MINUTES,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .coordinator import DishwasherSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Expose runtime tuning helper number entity."""

    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DurationMinutesHelper(coordinator)],
        update_before_add=True,
    )


class DurationMinutesHelper(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Default runtime"
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{CONF_DEFAULT_DURATION_MINUTES}"
        )

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

    @property
    def native_value(self) -> int:
        return self.coordinator.default_duration_minutes

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_option(
            CONF_DEFAULT_DURATION_MINUTES, int(value)
        )
