from __future__ import annotations

from datetime import time

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHEAPEST_HOUR_ENTITY,
    CONF_READY_SUBSTRING,
    CONF_PLANNING_MODE,
    CONF_PROGRAM_SELECT_ENTITY,
    CONF_START_BUTTON_ENTITY,
    CONF_STATUS_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_PLANNING_MODE,
    DEFAULT_READY_SUBSTRING,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
    MODE_CHEAPEST_24H,
    MODE_START_NOW,
)


def _ensure_time(value, default_value: str = DEFAULT_WINDOW_START) -> time:
    if isinstance(value, time):
        return value

    if isinstance(value, str):
        parsed = dt_util.parse_time(value)
        if parsed:
            return parsed

    try:
        hour = int(float(value))
        return time(hour % 24, 0)
    except (TypeError, ValueError):
        parsed_default = dt_util.parse_time(default_value)
        return parsed_default or time(0, 0)


def _time_to_str(value: time | str | int) -> str:
    if isinstance(value, str):
        parsed = dt_util.parse_time(value)
        if parsed:
            return parsed.strftime("%H:%M")
        return value
    if isinstance(value, time):
        return value.strftime("%H:%M")
    try:
        hour = int(float(value))
        return f"{hour:02d}:00"
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_START


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
        vol.Optional(CONF_PROGRAM_SELECT_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="select")
        ),
        vol.Required(
            CONF_PLANNING_MODE,
            default=DEFAULT_PLANNING_MODE,
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": MODE_CHEAPEST_24H, "label": "Cheapest in next 24h"},
                    {"value": MODE_START_NOW, "label": "Start now"},
                ]
            )
        ),
        vol.Optional(CONF_READY_SUBSTRING, default=DEFAULT_READY_SUBSTRING): str,
        vol.Optional(
            CONF_WINDOW_START, default=_ensure_time(DEFAULT_WINDOW_START)
        ): selector.TimeSelector(),
        vol.Optional(
            CONF_WINDOW_END, default=_ensure_time(DEFAULT_WINDOW_END)
        ): selector.TimeSelector(),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dishwasher Scheduler."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        title = "Dishwasher Scheduler"
        processed_input = dict(user_input)
        processed_input[CONF_WINDOW_START] = _time_to_str(
            user_input.get(CONF_WINDOW_START, DEFAULT_WINDOW_START)
        )
        processed_input[CONF_WINDOW_END] = _time_to_str(
            user_input.get(CONF_WINDOW_END, DEFAULT_WINDOW_END)
        )
        return self.async_create_entry(title=title, data=processed_input)

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
                        default=_ensure_time(
                            self.entry.options.get(
                                CONF_WINDOW_START,
                                self.entry.data.get(
                                    CONF_WINDOW_START, DEFAULT_WINDOW_START
                                ),
                            )
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_WINDOW_END,
                        default=_ensure_time(
                            self.entry.options.get(
                                CONF_WINDOW_END,
                                self.entry.data.get(
                                    CONF_WINDOW_END, DEFAULT_WINDOW_END
                                ),
                            )
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_PLANNING_MODE,
                        default=self.entry.options.get(
                            CONF_PLANNING_MODE,
                            self.entry.data.get(
                                CONF_PLANNING_MODE, DEFAULT_PLANNING_MODE
                            ),
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": MODE_CHEAPEST_24H,
                                    "label": "Cheapest in next 24h",
                                },
                                {"value": MODE_START_NOW, "label": "Start now"},
                            ]
                        )
                    ),
                    vol.Optional(
                        CONF_PROGRAM_SELECT_ENTITY,
                        default=self.entry.options.get(
                            CONF_PROGRAM_SELECT_ENTITY,
                            self.entry.data.get(CONF_PROGRAM_SELECT_ENTITY),
                        ),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="select")
                    ),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        processed_input = dict(user_input)
        processed_input[CONF_WINDOW_START] = _time_to_str(
            user_input.get(CONF_WINDOW_START, DEFAULT_WINDOW_START)
        )
        processed_input[CONF_WINDOW_END] = _time_to_str(
            user_input.get(CONF_WINDOW_END, DEFAULT_WINDOW_END)
        )
        return self.async_create_entry(title="", data=processed_input)
