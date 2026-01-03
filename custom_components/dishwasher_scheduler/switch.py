from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCH_ARMED
from .coordinator import DishwasherSchedulerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switch platform."""
    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DishwasherArmedSwitch(coordinator)], update_before_add=True)


class DishwasherArmedSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Armed"
    _attr_should_poll = False

    def __init__(self, coordinator: DishwasherSchedulerCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{SWITCH_ARMED}"

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
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.armed

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.set_armed(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.set_armed(False)
        self.async_write_ha_state()
