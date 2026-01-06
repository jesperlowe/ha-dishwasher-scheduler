from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, INTEGRATION_VERSION, CONF_WINDOW_START, CONF_WINDOW_END
from .coordinator import DishwasherSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up time helpers for Dishwasher Scheduler."""

    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WindowTimeHelper(coordinator, "Window start", CONF_WINDOW_START),
            WindowTimeHelper(coordinator, "Window end", CONF_WINDOW_END),
        ],
        update_before_add=True,
    )


class WindowTimeHelper(TimeEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: DishwasherSchedulerCoordinator, name: str, option_key: str
    ) -> None:
        self.coordinator = coordinator
        self._attr_name = name
        self._option_key = option_key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{option_key}"

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
    def native_value(self) -> time:
        if self._option_key == CONF_WINDOW_START:
            return self.coordinator.window_start
        return self.coordinator.window_end

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.async_update_option(
            self._option_key, value.strftime("%H:%M")
        )
