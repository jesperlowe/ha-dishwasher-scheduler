DOMAIN = "dishwasher_scheduler"
INTEGRATION_VERSION = "0.3.0"

CONF_CHEAPEST_HOUR_ENTITY = "cheapest_hour_entity"
CONF_STATUS_ENTITY = "status_entity"
CONF_START_BUTTON_ENTITY = "start_button_entity"
CONF_READY_SUBSTRING = "ready_substring"
CONF_WINDOW_START = "window_start"
CONF_WINDOW_END = "window_end"
CONF_PLANNING_MODE = "planning_mode"
CONF_PROGRAM_SELECT_ENTITY = "program_select_entity"

MODE_CHEAPEST_24H = "cheapest_24h"
MODE_START_NOW = "start_now"

DEFAULT_READY_SUBSTRING = "Ready"
DEFAULT_WINDOW_START = 0
DEFAULT_WINDOW_END = 0
DEFAULT_PLANNING_MODE = MODE_CHEAPEST_24H

PLATFORMS: list[str] = ["sensor", "switch"]

ATTR_LEVEL = "level"
ATTR_MESSAGE = "message"

SERVICE_LOG_MESSAGE = "log_message"
SERVICE_SCHEDULE_FROM_PRICES = "schedule_from_prices"

LOG_LEVELS = {
    "debug": "debug",
    "info": "info",
    "warning": "warning",
    "error": "error",
    "critical": "critical",
}

SENSOR_PLANNED_START = "planned_start"
SENSOR_LAST_ATTEMPT = "last_attempt"
SENSOR_LAST_RESULT = "last_result"

SWITCH_ARMED = "armed"
