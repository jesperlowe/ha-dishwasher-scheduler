DOMAIN = "dishwasher_scheduler"

CONF_CHEAPEST_HOUR_ENTITY = "cheapest_hour_entity"
CONF_STATUS_ENTITY = "status_entity"
CONF_START_BUTTON_ENTITY = "start_button_entity"
CONF_READY_SUBSTRING = "ready_substring"
CONF_WINDOW_START = "window_start"
CONF_WINDOW_END = "window_end"
CONF_PLANNING_MODE = "planning_mode"

MODE_CHEAPEST_24H = "cheapest_24h"
MODE_START_NOW = "start_now"

DEFAULT_READY_SUBSTRING = "Ready"
DEFAULT_WINDOW_START = 0
DEFAULT_WINDOW_END = 0
DEFAULT_PLANNING_MODE = MODE_CHEAPEST_24H

PLATFORMS: list[str] = ["sensor", "switch"]

SENSOR_PLANNED_START = "planned_start"
SENSOR_LAST_ATTEMPT = "last_attempt"
SENSOR_LAST_RESULT = "last_result"

SWITCH_ARMED = "armed"
