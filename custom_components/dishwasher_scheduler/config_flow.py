from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHEAPEST_HOUR_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig()
        ),
        vol.Required(CONF_STATUS_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig()
        ),
        vol.Required(CONF_START_BUTTON_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="button")
        ),
        vol.Optional(CONF_READY_SUBSTRING, default=DEFAULT_READY_SUBSTRING): str,
        vol.Optional(CONF_WINDOW_START, default=DEFAULT_WINDOW_START): vol.Coerce(int),
        vol.Optional(CONF_WINDOW_END, default=DEFAULT_WINDOW_END): vol.Coerce(int),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dishwasher Scheduler."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        title = "Dishwasher Scheduler"
        return self.async_create_entry(title=title, data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Dishwasher Scheduler."""

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_READY_SUBSTRING,
                        default=self.entry.options.get(
                            CONF_READY_SUBSTRING,
                            self.entry.data.get(
                                CONF_READY_SUBSTRING, DEFAULT_READY_SUBSTRING
                            ),
                        ),
                    ): str,
                    vol.Optional(
                        CONF_WINDOW_START,
                        default=self.entry.options.get(
                            CONF_WINDOW_START,
                            self.entry.data.get(CONF_WINDOW_START, DEFAULT_WINDOW_START),
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_WINDOW_END,
                        default=self.entry.options.get(
                            CONF_WINDOW_END,
                            self.entry.data.get(CONF_WINDOW_END, DEFAULT_WINDOW_END),
                        ),
                    ): vol.Coerce(int),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        return self.async_create_entry(title="", data=user_input)
