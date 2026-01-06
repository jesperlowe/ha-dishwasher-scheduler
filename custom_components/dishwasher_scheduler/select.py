from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PLANNING_MODE,
    DOMAIN,
    INTEGRATION_VERSION,
    MODE_CHEAPEST_24H,
    MODE_START_NOW,
)
from .coordinator import DishwasherSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the planning mode helper select."""

    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [PlanningModeSelect(coordinator)],
        update_before_add=True,
    )


class PlanningModeSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Planning mode"
    _attr_options = [MODE_CHEAPEST_24H, MODE_START_NOW]

    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{CONF_PLANNING_MODE}"

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
    def current_option(self) -> str | None:
        return self.coordinator.planning_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_update_option(CONF_PLANNING_MODE, option)
