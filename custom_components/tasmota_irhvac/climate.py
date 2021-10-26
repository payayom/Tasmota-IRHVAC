"""Adds support for generic thermostat units."""
import json
import logging
import uuid
import asyncio
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components import mqtt
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_IDLE,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_VERTICAL
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'irhvac'
VERSION = '1.0.0'

# Custom constants

# Some devices have "auto" and "fan_only" changed
HVAC_MODE_AUTO_FAN = "auto_fan_only"

# Some devicec have "fan_only" and "auto" changed
HVAC_MODE_FAN_AUTO = "fan_only_auto"

# HVAC mode list with 2 additional modes above
HVAC_MODES = [
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO
]

# Fan speeds
HVAC_FAN_AUTO = "auto"
HVAC_FAN_MIN = "min"
HVAC_FAN_MEDIUM = "medium"
HVAC_FAN_MAX = "max"

# Some devices say max,but it is high, and auto which is max
HVAC_FAN_MAX_HIGH = "max_high"
HVAC_FAN_AUTO_MAX = "auto_max"

# Fan speed list
HVAC_FAN_LIST = [
    HVAC_FAN_AUTO,
    HVAC_FAN_MIN,
    HVAC_FAN_MEDIUM,
    HVAC_FAN_MAX,
    HVAC_FAN_MAX_HIGH,
    HVAC_FAN_AUTO_MAX
]

# Swing mode list
HVAC_SWING_LIST = [
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_VERTICAL,
    SWING_OFF
]

# Vertical swing positions
SWING_HIGHEST = "highest"
SWING_HIGH = "high"
SWING_MIDDLE = "middle"
SWING_LOW = "low"
SWING_LOWEST = "lowest"

# Horizontal swing positions
SWING_MAXLEFT = "maxleft"
SWING_LEFT = "left"
SWING_CENTER = "center"
SWING_RIGHT = "right"
SWING_MAXRIGHT = "maxright"

SWING_AUTO = "auto"

# List of vertical swing positions
SWING_VERTICAL_LIST = [
    SWING_HIGHEST,
    SWING_HIGH,
    SWING_MIDDLE,
    SWING_LOW,
    SWING_LOWEST,
    SWING_AUTO
]

# List of horizontal swing positions
SWING_HORIZONTAL_LIST = [
    SWING_MAXLEFT,
    SWING_LEFT,
    SWING_CENTER,
    SWING_RIGHT,
    SWING_MAXRIGHT,
    SWING_AUTO
]

CONF_UNIQUE_ID = "unique_id"

# Platform specific config entry names
CONF_EXCLUSIVE_GROUP_VENDOR = "exclusive_group_vendor"
CONF_VENDOR = "vendor"
CONF_PROTOCOL = "protocol"  # Soon to be deprecated
CONF_COMMAND_TOPIC = "command_topic"
CONF_STATE_TOPIC = "state_topic"
CONF_TEMP_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TARGET_TEMP = "target_temp"
CONF_INITIAL_OPERATION_MODE = "initial_operation_mode"
CONF_INITIAL_FAN_MODE = "initial_fan_mode"
CONF_INITIAL_SWING_MODE = "initial_swing_mode"
CONF_INITIAL_VERTICAL_SWING_POSITION = "initial_vertical_swing_position"
CONF_INITIAL_HORIZONTAL_SWING_POSITION = "initial_horizontal_swing_position"
CONF_PRECISION = "precision"
CONF_MODES_LIST = "supported_modes"
CONF_FAN_LIST = "supported_fan_speeds"
CONF_SWING_LIST = "supported_swing_list"
CONF_QUIET = "default_quiet_mode"
CONF_TURBO = "default_turbo_mode"
CONF_ECONO = "default_econo_mode"
CONF_MODEL = "hvac_model"
CONF_CELSIUS = "celsius_mode"
CONF_LIGHT = "default_light_mode"
CONF_FILTER = "default_filter_mode"
CONF_CLEAN = "default_clean_mode"
CONF_BEEP = "default_beep_mode"
CONF_SLEEP = "default_sleep_mode"

# Platform specific default values
DEFAULT_NAME = "IR Air Conditioner"
DEFAULT_MIN_TEMP = 20
DEFAULT_MAX_TEMP = 30
DEFAULT_TARGET_TEMP = 26
DEFAULT_INITIAL_OPERATION_MODE = HVAC_MODE_OFF
DEFAULT_INITIAL_FAN_MODE = HVAC_FAN_AUTO
DEFAULT_INITIAL_SWING_MODE = SWING_BOTH
DEFAULT_INITIAL_VERTICAL_SWING_POSITION = SWING_AUTO
DEFAULT_INITIAL_HORIZONTAL_SWING_POSITION = SWING_AUTO
DEFAULT_PRECISION = 1
DEFAULT_CONF_QUIET = "off"
DEFAULT_CONF_TURBO = "off"
DEFAULT_CONF_ECONO = "off"
DEFAULT_CONF_MODEL = "-1"
DEFAULT_CONF_CELSIUS = "on"
DEFAULT_CONF_LIGHT = "off"
DEFAULT_CONF_FILTER = "off"
DEFAULT_CONF_CLEAN = "off"
DEFAULT_CONF_BEEP = "off"
DEFAULT_CONF_SLEEP = "-1"

DEFAULT_MODES_LIST = [
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY
]
DEFAULT_FAN_LIST = [HVAC_FAN_AUTO_MAX, HVAC_FAN_MEDIUM, HVAC_FAN_MIN]
DEFAULT_SWING_LIST = [SWING_OFF, SWING_VERTICAL]
DEFAULT_SWING_POSITION_LIST = HVAC_SWING_POSITION_LIST

# Attributes
ATTR_NAME = 'name'
ATTR_VALUE = 'value'
ATTR_SWINGV = 'swingv'
ATTR_SWINGH = 'swingh'
ATTR_ECONO = 'econo'
ATTR_TURBO = 'turbo'
ATTR_QUIET = 'quiet'
ATTR_LIGHT = 'light'
ATTR_FILTERS = 'filters'
ATTR_CLEAN = 'clean'
ATTR_BEEP = 'beep'
ATTR_SLEEP = 'sleep'

# Service names
SERVICE_SET_VERTICAL_SWING = 'set_swingv'
SERVICE_SET_HORIZONTAL_SWING = 'set_swingh'
SERVICE_ECONO_MODE = 'set_econo'
SERVICE_TURBO_MODE = 'set_turbo'
SERVICE_QUIET_MODE = 'set_quiet'
SERVICE_LIGHT_MODE = 'set_light'
SERVICE_FILTERS_MODE = 'set_filters'
SERVICE_CLEAN_MODE = 'set_clean'
SERVICE_BEEP_MODE = 'set_beep'
SERVICE_SLEEP_MODE = 'set_sleep'

# Map attributes to properties of the state object
ATTRIBUTES_IRHVAC = {
    ATTR_SWINGV: 'swingv',
    ATTR_SWINGH: 'swingh',
    ATTR_ECONO: 'econo',
    ATTR_TURBO: 'turbo',
    ATTR_QUIET: 'quiet',
    ATTR_LIGHT: 'light',
    ATTR_FILTERS: 'filters',
    ATTR_CLEAN: 'clean',
    ATTR_BEEP: 'beep',
    ATTR_SLEEP: 'sleep'
}

ON_OFF_LIST = [
    'ON',
    'OFF',
    'On',
    'Off',
    'on',
    'off'
]

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE)

DATA_KEY = 'tasmota_irhvac.climate'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Exclusive(CONF_VENDOR, CONF_EXCLUSIVE_GROUP_VENDOR): cv.string,
        vol.Exclusive(CONF_PROTOCOL, CONF_EXCLUSIVE_GROUP_VENDOR): cv.string,
        vol.Required(CONF_COMMAND_TOPIC): mqtt.valid_publish_topic,
        vol.Required(CONF_STATE_TOPIC): mqtt.valid_subscribe_topic,
        vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
        vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(CONF_INITIAL_OPERATION_MODE, default=DEFAULT_INITIAL_OPERATION_MODE): vol.In(HVAC_MODES),
        vol.Optional(CONF_INITIAL_FAN_MODE, default=DEFAULT_INITIAL_FAN_MODE): vol.In(HVAC_FAN_LIST),
        vol.Optional(CONF_INITIAL_SWING_MODE, default=DEFAULT_INITIAL_SWING_MODE): vol.In(HVAC_SWING_LIST),
        vol.Optional(CONF_INITIAL_VERTICAL_SWING_POSITION, default=DEFAULT_INITIAL_VERTICAL_SWING_POSITION): vol.In(SWING_VERTICAL_LIST),
        vol.Optional(CONF_INITIAL_HORIZONTAL_SWING_POSITION, default=DEFAULT_INITIAL_HORIZONTAL_SWING_POSITION): vol.In(SWING_HORIZONTAL_LIST),
        vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): vol.In(
            [PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]
        ),
        vol.Optional(CONF_MODE_LIST, default=DEFAULT_MODE_LIST): vol.All(
            cv.ensure_list, [vol.In(HVAC_MODES)]
        ),
        vol.Optional(CONF_FAN_LIST, default=DEFAULT_FAN_LIST): vol.All(
            cv.ensure_list, [vol.In(HVAC_FAN_LIST)]
        ),
        vol.Optional(CONF_SWING_LIST, default=DEFAULT_SWING_LIST): vol.All(
            cv.ensure_list, [vol.In(HVAC_SWING_LIST)]
        ),
        vol.Optional(CONF_QUIET, default=DEFAULT_CONF_QUIET): cv.string,
        vol.Optional(CONF_TURBO, default=DEFAULT_CONF_TURBO): cv.string,
        vol.Optional(CONF_ECONO, default=DEFAULT_CONF_ECONO): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_CONF_MODEL): cv.string,
        vol.Optional(CONF_CELSIUS, default=DEFAULT_CONF_CELSIUS): cv.string,
        vol.Optional(CONF_LIGHT, default=DEFAULT_CONF_LIGHT): cv.string,
        vol.Optional(CONF_FILTER, default=DEFAULT_CONF_FILTER): cv.string,
        vol.Optional(CONF_CLEAN, default=DEFAULT_CONF_CLEAN): cv.string,
        vol.Optional(CONF_BEEP, default=DEFAULT_CONF_BEEP): cv.string,
        vol.Optional(CONF_SLEEP, default=DEFAULT_CONF_SLEEP): cv.string
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the irhvac platform."""
    async_add_entities([IRhvac(hass, config)])

class IRhvac(ClimateEntity, RestoreEntity):
    def __init__(self, hass, config):
        self.hass = hass
        self._name = config[CONF_NAME]
        self._unique_id = config[CONF_UNIQUE_ID]
        self._topic = config[CONF_COMMAND_TOPIC]
        self._state_topic = config[CONF_STATE_TOPIC]
        self._vendor = config[CONF_VENDOR]
        self._protocol = config[CONF_PROTOCOL]
        self._temperature_sensor = config[CONF_TEMP_SENSOR]
        self._humidity_sensor = config[CONF_HUMIDITY_SENSOR]
        self._current_temperature = None
        self._current_humidity = None
        self._min_temp = config[CONF_MIN_TEMP]
        self._max_temp = config[CONF_MAX_TEMP]
        self._target_temp = config[CONF_TARGET_TEMP]
        self._temp_precision = config[CONF_PRECISION]
        self._hvac_list = config[CONF_MODE_LIST]
        self._hvac_mode = config[CONF_INITIAL_OPERATION_MODE]
        self._last_on_mode = None
        self._fan_list = config[CONF_FAN_LIST]
        self._fan_mode = config[CONF_INITIAL_FAN_MODE]
        self._swing_list = config[CONF_SWING_LIST]
        self._unit = hass.config.units.temperature_unit
        self._quiet = config[CONF_QUIET]
        self._turbo = config[CONF_TURBO]
        self._econo = config[CONF_ECONO]
        self._model = config[CONF_MODEL]
        self._celsius = config[CONF_CELSIUS]
        self._light = config[CONF_LIGHT]
        self._filters = config[CONF_FILTER]
        self._clean = config[CONF_CLEAN]
        self._beep = config[CONF_BEEP]
        self._sleep = config[CONF_SLEEP]
        self._power_mode = STATE_OFF
        self._enabled = False

        # Some AC models require explicit power flag in IRHVAC command so self._power_mode should be set to STATE_ON for all HVAC modes except HVAC_MODE_OFF
        if self._hvac_mode is not HVAC_MODE_OFF:
            self._power_mode = STATE_ON
            self._enabled = True
        
        if self._vendor is None:
            if self._protocol is None:
                _LOGGER.error('Neither vendor nor protocol provided for "%s"!', self._unique_id)
                return
            self._vendor = self._protocol
            
        self._support_flags = SUPPORT_FLAGS
        if self._swing_list:
            self._support_flags = self.support_flags | SUPPORT_SWING_MODE
            self._swing_mode = config[CONF_INITIAL_SWING_MODE]
            self._swingv_position = config[CONF_INITIAL_VERTICAL_SWING_POSITION]
            self._swingh_position = config[CONF_INITIAL_HORIZONTAL_SWING_POSITION]
        
        self._sub_state = None
        self._state_attrs = {}
        self._state_attrs.update(
            {attribute: getattr(self, '_' + attribute)
             for attribute in ATTRIBUTES_IRHVAC}
        )
        
        self._temp_lock = asyncio.Lock()
              
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        if self._temperature_sensor is not None:
            async_track_state_change(
                self.hass, self._temperature_sensor, self._async_temperature_sensor_changed
            )
            sensor_state = self.hass.states.get(self._temperature_sensor)
            if sensor_state and sensor_state.state != STATE_UNAVAILABLE:
                self._async_update_temperature(sensor_state)

        if self._humidity_sensor is not None:
            async_track_state_change(
                self.hass, self._humidity_sensor, self._async_humidity_sensor_changed
            )
            sensor_state = self.hass.states.get(self._humidity_sensor)
            if sensor_state and sensor_state.state != STATE_UNAVAILABLE:
                self._async_update_humidity(sensor_state)
        
        await self._subscribe_topics()

#         self.hass.bus.async_listen_once(
#             EVENT_HOMEASSISTANT_START, _async_startup)

        # Check If we have an old state
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._hvac_mode = last_state.state
            self._fan_mode = last_state.attributes[ATTR_FAN_MODE]
            self._target_temp = last_state.attributes[ATTR_TEMPERATURE]
            if self._swing_list:
                self._swing_mode = last_state.attributes['swing_mode']
                self._swingv_position = last_state.attributes['swingv']
                self._swingh_position = last_state.attributes['swingh']

            if self._hvac_mode != HVAC_MODE_OFF:
                self._last_on_mode = self._hvac_mode
                self._power_mode = STATE_ON
                self._enabled = True
            else:
                self._power_mode = STATE_OFF
                self._enabled = False

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        def state_message_received(msg):
            """Handle new MQTT state messages."""
            json_payload = json.loads(msg.payload)
            _LOGGER.debug("Payload received: %s", json_payload)

            # If listening to `tele`, result looks like: {"IrReceived":{"Protocol":"XXX", ... ,"IRHVAC":{ ... }}}
            # we want to extract the data.
            if "IrReceived" in json_payload:
                json_payload = json_payload["IrReceived"]

            # By now the payload must include an `IRHVAC` field.
            if "IRHVAC" not in json_payload:
                return

            payload = json_payload["IRHVAC"]

            if payload["Vendor"] == self._vendor:
                # All values in the payload are Optional
                if "Power" in payload:
                    self._power_mode = payload["Power"].lower()
                if "Mode" in payload:
                    self._hvac_mode = payload["Mode"].lower()
                if "Temp" in payload:
                    if payload["Temp"] > 0:
                        self._target_temp = payload["Temp"]
                if "Celsius" in payload:
                    self._celsius = payload["Celsius"].lower()
                if "Quiet" in payload:
                    self._quiet = payload["Quiet"].lower()
                if "Turbo" in payload:
                    self._turbo = payload["Turbo"].lower()
                if "Econo" in payload:
                    self._econo = payload["Econo"].lower()
                if "Light" in payload:
                    self._light = payload["Light"].lower()
                if "Filter" in payload:
                    self._filters = payload["Filter"].lower()
                if "Clean" in payload:
                    self._clean = payload["Clean"].lower()
                if "Beep" in payload:
                    self._beep = payload["Beep"].lower()
                if "Sleep" in payload:
                    self._sleep = payload["Sleep"]
                self._swingv_position = SWING_OFF
                self._swingh_position = SWING_OFF
                if "SwingV" in payload and (SWING_VERTICAL in self._swing_list or SWING_BOTH in self._swing_list):
                    self._swingv_position = payload["SwingV"].lower()
                if "SwingH" in payload and (SWING_HORIZONTAL in self._swing_list or SWING_BOTH in self._swing_list):
                    self._swingh_position = payload["SwingH"].lower()
                if self._swingv_position is not None and self._swingv_position == SWING_AUTO:
                    if self._swingh_position is not None and self._swingh_position == SWING_AUTO:
                        self._swing_mode = SWING_BOTH
                    else:
                        self._swing_mode = SWING_VERTICAL
                elif self._swingh_position is not None and self._swingh_position == SWING_AUTO:
                    self._swing_mode = SWING_HORIZONTAL
                else:
                    self._swing_mode = SWING_OFF

                if "FanSpeed" in payload:
                    fan_mode = payload["FanSpeed"].lower()
                    # ELECTRA_AC fan modes fix
                    if (
                        HVAC_FAN_MAX_HIGH in self._fan_list
                        and HVAC_FAN_AUTO_MAX in self._fan_list
                    ):
                        if fan_mode == HVAC_FAN_MAX:
                            self._fan_mode = FAN_HIGH
                        elif fan_mode == HVAC_FAN_AUTO:
                            self._fan_mode = HVAC_FAN_MAX
                        else:
                            self._fan_mode = fan_mode
                    else:
                        self._fan_mode = fan_mode
                    _LOGGER.debug("Fan Mode: %s", self._fan_mode)

                # Set default state to off
                if self._power_mode == STATE_OFF:
                    self._enabled = False
                    self._hvac_mode = HVAC_MODE_OFF
                else:
                    self._enabled = True

                # Update state attributes
                self._state_attrs.update(
                    {attribute: getattr(self, '_' + attribute)
                     for attribute in ATTRIBUTES_IRHVAC}
                )
                # Update HA UI and State
                self.schedule_update_ha_state()

        self._sub_state = await mqtt.subscription.async_subscribe_topics(
            self.hass,
            self._sub_state,
            {
                CONF_STATE_TOPIC: {
                    "topic": self._state_topic,
                    "msg_callback": state_message_received,
                    "qos": 1,
                }
            },
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await mqtt.subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique_id of the thermostat."""
        return self._unique_id

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._temp_precision

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp
    
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature
    
    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._current_temperature
    
    @property
    def current_humidity(self):
        """Return the sensor humidity."""
        return self._current_humidity
    
    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVAC_MODE_HEAT:
            return CURRENT_HVAC_HEAT
        elif self._hvac_mode == HVAC_MODE_COOL:
            return CURRENT_HVAC_COOL
        elif self._hvac_mode == HVAC_MODE_DRY:
            return CURRENT_HVAC_DRY
        elif self._hvac_mode == HVAC_MODE_FAN_ONLY:
            return CURRENT_HVAC_FAN
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_list

    @property
    def last_on_mode(self):
        """Return the last non HVAC_MODE_OFF mode."""
        return self._last_on_mode
    
    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._fan_list

    @property
    def swing_mode(self):
        """Return the swing setting."""
        return self._swing_mode

    @property
    def swing_modes(self):
        """Return the list of available swing modes."""
        return self._swing_list

    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self.power_mode == STATE_ON

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    # main commands that correspond to standard service calls
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode not in self._hvac_list:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return
        self._hvac_mode = hvac_mode
        if hvac_mode == HVAC_MODE_OFF:
            self._enabled = False
            self.power_mode = STATE_OFF
        else:
            self._last_on_mode = hvac_mode
            self._enabled = True
            self.power_mode = STATE_ON
        
        # Ensure we update the current operation after changing the mode
        await self.async_send_cmd(False)

    async def async_turn_on(self):
        """Turn thermostat on."""
        if self._last_on_mode is not None: # if last mode is defined, set to it to turn on (assuming the thermostat is currently off)
            await self.async_set_hvac_mode(self, self._last_on_mode)
        elif DEFAULT_HVAC_MODE != HVAC_MODE_OFF: # if not and default hvac mode is not HVAC_MODE_OFF set to default hvac mode
            await self.async_set_hvac_mode(self, DEFAULT_HVAC_MODE) 
 
    async def async_turn_off(self):
        """Turn thermostat off."""
        await self.async_set_hvac_mode(self, HVAC_MODE_OFF)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if temperature < self._min_temp or temperature > self._max_temp:
            _LOGGER.warning('The temperature value is out of range')
            return
        if self._precision == PRECISION_WHOLE:
            self._target_temp = round(temperature)
        elif self._precision == PRECISION_HALVES:
            self._target_temp = round(temperature * 2) / 2
        else: # default to 1 decimal place
            self._target_temp = round(temperature, 1)
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(False)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode not in self._fan_list:
            _LOGGER.error(
                "Invalid fan mode selected. Got '%s'. Allowed modes are:", fan_mode
            )
            _LOGGER.error(self._fan_list)
            return
        self._fan_mode = fan_mode
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if swing_mode not in self._swing_list:
            _LOGGER.error(
                "Invalid swing mode selected. Got '%s'. Allowed modes are:", swing_mode
            )
            _LOGGER.error(self._swing_list)
            return
        self._swing_mode = swing_mode
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_econo(self, econo):
        """Set new target econo mode."""
        if econo not in ON_OFF_LIST:
            return
        self._econo = econo.lower()
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_turbo(self, turbo):
        """Set new target turbo mode."""
        if turbo not in ON_OFF_LIST:
            return
        self._turbo = turbo.lower()
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_quiet(self, quiet):
        """Set new target quiet mode."""
        if quiet not in ON_OFF_LIST:
            return
        self._quiet = quiet.lower()
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_clean(self, clean):
        """Set new target clean mode."""
        if clean not in ON_OFF_LIST:
            return
        self._clean = clean.lower()
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_set_sleep(self, sleep):
        """Set new target sleep mode."""
        self._sleep = sleep.lower()
        if self._hvac_mode != HVAC_MODE_OFF:
            await self.async_send_cmd(True)

    async def async_send_cmd(self, attr_update=False):
        if attr_update:
            await self.async_update_state_attrs()
        await self.hass.async_add_executor_job(self.send_ir)
        await self.async_update_ha_state()

    async def async_update_state_attrs(self):
        self._state_attrs.update(
            {attribute: getattr(self, '_' + attribute)
             for attribute in ATTRIBUTES_IRHVAC}
        )

    async def _async_temperature_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is not None:
            self._async_update_temperature(new_state)
            await self.async_update_ha_state()

    @callback
    def _async_update_temperature(self, state):
        """Update thermostat with latest state from temperature sensor."""
        try:
            if state.state != STATE_UNAVAILABLE:
                self._current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.debug("Unable to update from temperature sensor: %s", ex)

    async def _async_humidity_sensor_changed(self, entity_id, old_state, new_state):
        """Handle humidity changes."""
        if new_state is not None:
            self._async_update_humidity(new_state)
            await self.async_update_ha_state()

    @callback
    def _async_update_humidity(self, state):
        """Update thermostat with latest state from humidity sensor."""
        try:
            if state.state != STATE_UNAVAILABLE:
                self._current_humidity = float(state.state)
        except ValueError as ex:
            _LOGGER.debug("Unable to update from humidity sensor: %s", ex)
            
    def send_ir(self):
        """Send the payload to tasmota mqtt topic."""
        # Set the vertical and horizontal swing positions, default to 'auto'
        swing_v = SWING_AUTO
        swing_h = SWING_AUTO
        if self._swing_mode == SWING_VERTICAL:
            swing_h = self._swingh_position
        elif self.swing_mode == SWING_HORIZONTAL:
            swing_v = self._swingv_position
        elif self.swing_mode == SWING_OFF:
            swing_v = SWING_OFF
            swing_h = SWING_OFF
        # Populate the payload
        payload_data = {
            "Vendor": self._vendor,
            "Model": self._model,
            "Power": self._power_mode,
            "Mode": self._hvac_mode,
            "Celsius": self._celsius,
            "Temp": self._target_temp,
            "FanSpeed": self._fan_mode,
            "SwingV": swing_v,
            "SwingH": swing_h,
            "Quiet": self._quiet,
            "Turbo": self._turbo,
            "Econo": self._econo,
            "Clean": self._clean,
            "Sleep": self._sleep
        }
        payload = (json.dumps(payload_data))
        _LOGGER.debug("Payload to publish: %s", payload)
        # Publish mqtt message
        mqtt.async_publish(self.hass, self._topic, payload)
