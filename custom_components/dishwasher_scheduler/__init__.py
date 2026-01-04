from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    ATTR_LEVEL,
    ATTR_MESSAGE,
    DOMAIN,
    INTEGRATION_VERSION,
    LOG_LEVELS,
    PLATFORMS,
    SERVICE_LOG_MESSAGE,
    SERVICE_SCHEDULE_FROM_PRICES,
)
from .coordinator import DishwasherSchedulerCoordinator

_LOGGER = logging.getLogger(__name__)


def _log_with_level(level: str, message: str) -> None:
    log_method = getattr(_LOGGER, level, _LOGGER.info)
    log_method(message)


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_LOG_MESSAGE):
        return

    async def _handle_log_service(call: ServiceCall) -> None:
        level = call.data[ATTR_LEVEL]
        message = call.data[ATTR_MESSAGE]
        _log_with_level(level, f"[Dishwasher Scheduler] {message}")

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_MESSAGE,
        _handle_log_service,
        schema=vol.Schema(
            {
                vol.Required(ATTR_MESSAGE): str,
                vol.Optional(ATTR_LEVEL, default="info"): vol.In(LOG_LEVELS),
            }
        ),
    )

    async def _handle_schedule_service(call: ServiceCall) -> None:
        if not hass.data.get(DOMAIN):
            _LOGGER.warning("No Dishwasher Scheduler entries available for scheduling")
            return

        coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN][
            next(iter(hass.data[DOMAIN]))
        ]

        price_entity = call.data["price_entity"]
        duration_half_hours = call.data.get("duration_half_hours", 2)
        program_durations = call.data.get("program_durations")
        arm = call.data.get("arm", True)

        await coordinator.async_schedule_from_prices(
            price_entity,
            duration_half_hours,
            program_durations,
            arm,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_FROM_PRICES,
        _handle_schedule_service,
        schema=vol.Schema(
            {
                vol.Required("price_entity"): str,
                vol.Optional("duration_half_hours", default=2): vol.Coerce(int),
                vol.Optional("program_durations"): {str: vol.Coerce(int)},
                vol.Optional("arm", default=True): bool,
            }
        ),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dishwasher Scheduler from a config entry."""
    _LOGGER.info(
        "Setting up Dishwasher Scheduler v%s for entry %s",
        INTEGRATION_VERSION,
        entry.entry_id,
    )

    await _async_register_services(hass)

    coordinator = DishwasherSchedulerCoordinator(hass, entry)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: DishwasherSchedulerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_LOG_MESSAGE)
        _LOGGER.info("Removed Dishwasher Scheduler services (no entries left)")

    return unloaded
