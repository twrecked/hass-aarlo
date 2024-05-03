"""
Support for Arlo Alarm Control Panels.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://home-assistant.io/components/alarm_control_panel.arlo
"""

import logging
import re
from collections.abc import Callable
from typing import Any

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    CodeFormat
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_ENTITY_ID,
    CONF_CODE,
    CONF_TRIGGER_TIME,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import HomeAssistant, HassJob
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry

from pyaarlo.constant import (
    MODE_KEY,
    SIREN_STATE_KEY
)

from .const import *
from .utils import get_entity_from_domain

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_CODE): cv.string,
    vol.Optional(CONF_CODE_ARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_CODE_DISARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_COMMAND_TEMPLATE, default=DEFAULT_COMMAND_TEMPLATE): cv.template,
    vol.Optional(CONF_DISARMED_MODE_NAME, default=STATE_ALARM_DISARMED): cv.string,
    vol.Optional(CONF_HOME_MODE_NAME, default=STATE_ALARM_ARLO_HOME): cv.string,
    vol.Optional(CONF_AWAY_MODE_NAME, default=STATE_ALARM_ARLO_ARMED): cv.string,
    vol.Optional(CONF_NIGHT_MODE_NAME, default=STATE_ALARM_ARLO_NIGHT): cv.string,
    vol.Optional(CONF_ALARM_VOLUME, default=DEFAULT_ALARM_VOLUME): cv.string,
    vol.Optional(CONF_TRIGGER_TIME, default=DEFAULT_TRIGGER_TIME): vol.All(
        cv.time_period, cv.positive_timedelta
    ),
})

ATTR_MODE = "mode"
ATTR_VOLUME = "volume"
ATTR_DURATION = "duration"
ATTR_TIME_ZONE = "time_zone"

SERVICE_MODE = "alarm_set_mode"
SERVICE_MODE_SCHEMA = vol.Schema({
        vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
        vol.Required(ATTR_MODE): cv.string,
})
SERVICE_SIREN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_DURATION): cv.positive_int,
    vol.Required(ATTR_VOLUME): cv.positive_int,
})
SERVICE_SIREN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
})

WS_TYPE_SIREN_ON = "aarlo_alarm_siren_on"
WS_TYPE_SIREN_OFF = "aarlo_alarm_siren_off"
SCHEMA_WS_SIREN_ON = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
        vol.Required("type"): WS_TYPE_SIREN_ON,
        vol.Required("entity_id"): cv.entity_id,
        vol.Required(ATTR_DURATION): cv.positive_int,
        vol.Required(ATTR_VOLUME): cv.positive_int,
})
SCHEMA_WS_SIREN_OFF = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_SIREN_OFF, vol.Required("entity_id"): cv.entity_id
})


async def async_setup_entry(
        hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up the Arlo Alarm Control Panels."""

    arlo = hass.data[COMPONENT_DATA]
    if not arlo.base_stations:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]
    config = hass.data[COMPONENT_CONFIG][ALARM_DOMAIN]
    _LOGGER.debug(f"alarm={config}")

    base_stations = []
    base_stations_with_sirens = False
    for base_station in arlo.base_stations:
        base_stations.append(ArloBaseStation(base_station, aarlo_config, config))
        if base_station.has_capability(SIREN_STATE_KEY):
            base_stations_with_sirens = True

    async_add_entities(base_stations)

    _LOGGER.debug("Adding Locations")
    locations = []
    for location in arlo.locations:
        _LOGGER.debug("Locations Iterator")
        locations.append(ArloLocation(location, aarlo_config, config))

    async_add_entities(locations)

    # Component services
    def service_callback(call):
        """Call aarlo service handler."""
        _LOGGER.debug(f"{call.service} service called")
        if call.service == SERVICE_MODE:
            alarm_mode_service(hass, call)

    async def async_service_callback(call):
        # pass off to background thread
        await hass.async_add_executor_job(service_callback, call)

    if not hasattr(hass.data[COMPONENT_SERVICES], ALARM_DOMAIN):
        _LOGGER.debug("installing handlers")
        hass.data[COMPONENT_SERVICES][ALARM_DOMAIN] = "installed"
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_MODE,
            async_service_callback,
            schema=SERVICE_MODE_SCHEMA,
        )

    # Websockets.
    if base_stations_with_sirens:
        websocket_api.async_register_command(
            hass, WS_TYPE_SIREN_ON, websocket_siren_on, SCHEMA_WS_SIREN_ON
        )
        websocket_api.async_register_command(
            hass, WS_TYPE_SIREN_OFF, websocket_siren_off, SCHEMA_WS_SIREN_OFF
        )


def _code_format(code):
    """Return one or more digits/characters."""
    if code is None or code == "":
        return None
    if isinstance(code, str) and re.search("^\\d+$", code):
        return CodeFormat.NUMBER
    return CodeFormat.TEXT


def _code_validate(code, code_to_check, state):
    """Validate given code."""
    if code is None or code == "":
        return True
    if code_to_check != code:
        _LOGGER.warning(f"Wrong code entered for {state}")
        return False
    return True


def _get_base_from_entity_id(hass, entity_id):
    component = hass.data.get(ALARM_DOMAIN)
    if component is None:
        raise HomeAssistantError("base component not set up")

    location = component.get_entity(entity_id)
    if location is None:
        raise HomeAssistantError("base not found")

    return location


def _get_location_from_entity_id(hass, entity_id):
    component = hass.data.get(ALARM_DOMAIN)
    if component is None:
        raise HomeAssistantError("location component not set up")

    location = component.get_entity(entity_id)
    if location is None:
        raise HomeAssistantError("location not found")

    return location


class ArloBaseStation(AlarmControlPanelEntity):
    """Representation of an Arlo Alarm Control Panel."""

    _timer: Callable[[], None] | None = None

    def __init__(self, device, aarlo_config, config):
        """Initialize the alarm control panel."""
        self._base = device

        self._disarmed_mode_name = config.get(CONF_DISARMED_MODE_NAME).lower()
        self._home_mode_name = config.get(CONF_HOME_MODE_NAME).lower()
        self._away_mode_name = config.get(CONF_AWAY_MODE_NAME).lower()
        self._night_mode_name = config.get(CONF_NIGHT_MODE_NAME).lower()
        self._alarm_volume = config.get(CONF_ALARM_VOLUME)
        self._trigger_time = config.get(CONF_TRIGGER_TIME)
        self._trigger_till = None
        self._attr_state = None
        self._code = config.get(CONF_CODE)
        self._timer = None
        _LOGGER.debug(f"alarm-code={self._code}")

        self._attr_name = device.name
        self._attr_unique_id = device.entity_id
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{ALARM_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"
        _LOGGER.debug(f"alarm-entity-id={self.entity_id}")

        self._attr_code_format = _code_format(config.get(CONF_CODE))
        self._attr_code_arm_required = config.get(CONF_CODE_ARM_REQUIRED)
        self._attr_code_disarm_required = config.get(CONF_CODE_DISARM_REQUIRED)
        self._attr_icon = ALARM_ICON
        self._attr_should_poll = False
        self._attr_supported_features = AlarmControlPanelEntityFeature(
            AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY |
            AlarmControlPanelEntityFeature.ARM_NIGHT | AlarmControlPanelEntityFeature.TRIGGER
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._base.device_id)},
            manufacturer=COMPONENT_BRAND,
        )
        _LOGGER.info(f"ArloBaseStation: {self._attr_name} created")

    def _get_state_from_ha(self, mode):
        """Convert Arlo mode to Home Assistant state."""
        lmode = mode.lower()
        if lmode == self._disarmed_mode_name:
            return STATE_ALARM_DISARMED
        if lmode == self._away_mode_name:
            return STATE_ALARM_ARMED_AWAY
        if lmode == self._home_mode_name:
            return STATE_ALARM_ARMED_HOME
        if lmode == self._night_mode_name:
            return STATE_ALARM_ARMED_NIGHT
        if lmode == STATE_ALARM_ARLO_ARMED:
            return STATE_ALARM_ARMED_AWAY
        return mode

    async def _async_stop_trigger(self, *_args: Any) -> None:
        if self._trigger_till is not None:
            _LOGGER.info(f"{self._attr_name}: untriggered")
            self.alarm_clear()
            self._trigger_till = None
            self.async_schedule_update_ha_state()

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, _attr, _value):
            _LOGGER.debug("callback:{self._attr_name}:{attr}:{str(value)}")
            self._attr_state = self._get_state_from_ha(self._base.attribute(MODE_KEY))
            self.schedule_update_ha_state()

        self._attr_state = self._get_state_from_ha(self._base.attribute(MODE_KEY, STATE_ALARM_ARLO_ARMED))
        self._base.add_attr_callback(MODE_KEY, update_state)

    @property
    def state(self):
        """Return the state of the device."""
        if self._trigger_till is not None:
            return STATE_ALARM_TRIGGERED
        return self._attr_state

    def alarm_disarm(self, code=None):
        if self._attr_code_disarm_required and not _code_validate(self._code, code, "disarming"):
            return
        self.set_mode_in_ha(self._disarmed_mode_name)

    def alarm_arm_away(self, code=None):
        if self._attr_code_arm_required and not _code_validate(self._code, code, "arming away"):
            return
        self.set_mode_in_ha(self._away_mode_name)

    def alarm_arm_home(self, code=None):
        if self._attr_code_arm_required and not _code_validate(self._code, code, "arming home"):
            return
        self.set_mode_in_ha(self._home_mode_name)

    def alarm_arm_night(self, code=None):
        if self._attr_code_arm_required and not _code_validate(self._code, code, "arming night"):
            return
        self.set_mode_in_ha(self._night_mode_name)

    def alarm_trigger(self, code=None):
        if self._trigger_till is None:
            _LOGGER.info(f"{self._attr_name}: triggered")
            if int(self._alarm_volume) != 0:
                self._base.siren_on(
                    duration=self._trigger_time.total_seconds(),
                    volume=self._alarm_volume,
                )
            self._trigger_till = dt_util.utcnow() + self._trigger_time
            self._timer = async_track_point_in_time(
                self.hass, HassJob(self._async_stop_trigger), self._trigger_till
            )
            self.schedule_update_ha_state()

    def alarm_clear(self):
        self._trigger_till = None
        self._base.siren_off()

    def alarm_arm_custom_bypass(self, code=None):
        pass

    def restart(self):
        self._base.restart()

    def set_mode_in_ha(self, mode):
        """convert Home Assistant state to Arlo mode."""
        lmode = mode.lower()
        if lmode == self._disarmed_mode_name:
            if self._trigger_till is not None:
                _LOGGER.debug(f"{self._attr_name} disarming/silencing")
                self.alarm_clear()
        _LOGGER.debug(f"{self._attr_name} set mode to {lmode}")
        self._base.mode = lmode

    def siren_on(self, duration=30, volume=10):
        if self._base.has_capability(SIREN_STATE_KEY):
            _LOGGER.debug(f"{self._attr_name} siren on {volume}/{duration}")
            self._base.siren_on(duration=duration, volume=volume)
            return True
        return False

    def siren_off(self):
        if self._base.has_capability(SIREN_STATE_KEY):
            _LOGGER.debug(f"{self._attr_name} siren off")
            self._base.siren_off()
            return True
        return False

    async def async_siren_on(self, duration, volume):
        return await self.hass.async_add_executor_job(self.siren_on, duration, volume)

    async def async_siren_off(self):
        return await self.hass.async_add_executor_job(self.siren_off)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "device_brand": COMPONENT_BRAND,
            "device_id": self._base.device_id,
            "device_model": self._base.model_id,
            "on_schedule": self._base.on_schedule,
            "siren": self._base.has_capability(SIREN_STATE_KEY),
        }


class ArloLocation(AlarmControlPanelEntity):
    """Representation of an Arlo Alarm Control Panel."""

    def __init__(self, location, aarlo_config, config):
        """Initialize the alarm control panel."""

        self._location = location

        self._attr_state = None
        self._code = config.get(CONF_CODE)

        self._attr_name = location.name
        self._attr_unique_id = location.entity_id
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{ALARM_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"

        self._attr_code_format = _code_format(config.get(CONF_CODE))
        self._attr_code_arm_required = config.get(CONF_CODE_ARM_REQUIRED)
        self._attr_code_disarm_required = config.get(CONF_CODE_DISARM_REQUIRED)
        self._attr_icon = ALARM_ICON
        self._attr_should_poll = False
        self._attr_supported_features = AlarmControlPanelEntityFeature(
            AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._location.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"ArloLocation: {self._attr_name} created")

    def _get_state_from_ha(self, mode):
        """Convert Arlo mode to Home Assistant state."""
        _LOGGER.info(f"{self._attr_name}: mode check: mode={mode}")
        if self._location.is_armed_away:
            return STATE_ALARM_ARMED_AWAY
        if self._location.is_armed_home:
            return STATE_ALARM_ARMED_HOME
        return STATE_ALARM_DISARMED

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)}")
            self._attr_state = self._get_state_from_ha(self._location.attribute(MODE_KEY))
            self.schedule_update_ha_state()

        self._attr_state = self._get_state_from_ha(self._location.attribute(MODE_KEY, "Stand By"))
        self._location.add_attr_callback(MODE_KEY, update_state)

    def alarm_disarm(self, code=None):
        _LOGGER.debug(f"Location {self._attr_name} disarm.  Code: {code}")
        if self._attr_code_disarm_required and not _code_validate(self._code, code, "disarming"):
            return
        self._location.stand_by()

    def alarm_arm_away(self, code=None):
        _LOGGER.debug(f"Location {self._attr_name} arm away.  Code: {code}")
        if self._attr_code_arm_required and not _code_validate(self._code, code, "arming away"):
            return
        self._location.arm_away()

    def alarm_arm_home(self, code=None):
        _LOGGER.debug(f"Location {self._attr_name} arm home.  Code: {code}")
        if self._attr_code_arm_required and not _code_validate(self._code, code, "arming home"):
            return
        self._location.arm_home()

    def alarm_trigger(self, code=None):
        pass

    def alarm_clear(self):
        pass

    def alarm_arm_custom_bypass(self, code=None):
        pass

    def restart(self):
        pass

    def set_mode_in_ha(self, mode):
        """convert Home Assistant state to Arlo mode."""
        _LOGGER.debug(f"{self._attr_name} set mode to {mode}")
        self._location.mode = mode

    def siren_on(self, duration=30, volume=10):
        pass

    def siren_off(self):
        pass

    async def async_siren_on(self, duration, volume):
        pass

    async def async_siren_off(self):
        pass

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "device_brand": COMPONENT_BRAND,
        }


@websocket_api.async_response
async def websocket_siren_on(hass, connection, msg):
    base = _get_base_from_entity_id(hass, msg["entity_id"])
    _LOGGER.debug(f"start siren for {msg['entity_id']}")

    await base.async_siren_on(duration=msg["duration"], volume=msg["volume"])
    connection.send_message(websocket_api.result_message(msg["id"], {"siren": "on"}))


@websocket_api.async_response
async def websocket_siren_off(hass, connection, msg):
    base = _get_base_from_entity_id(hass, msg["entity_id"])
    _LOGGER.debug(f"stop siren for {msg['entity_id']}")

    await base.async_siren_off()
    connection.send_message(websocket_api.result_message(msg["id"], {"siren": "off"}))


async def aarlo_mode_service_handler(base, service):
    mode = service.data[ATTR_MODE]
    base.set_mode_in_ha(mode)


async def aarlo_siren_on_service_handler(base, service):
    volume = service.data[ATTR_VOLUME]
    duration = service.data[ATTR_DURATION]
    base.siren_on(duration=duration, volume=volume)


async def aarlo_siren_off_service_handler(base, _service):
    base.siren_off()


def alarm_mode_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            mode = call.data["mode"]
            get_entity_from_domain(hass, ALARM_DOMAIN, entity_id).set_mode_in_ha(mode)
            _LOGGER.debug(f"{entity_id} setting mode to {mode}")
        except HomeAssistantError:
            _LOGGER.warning(f"{entity_id} is not an aarlo alarm device")
