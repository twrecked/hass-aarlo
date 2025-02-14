"""
Handles the file based Aarlo configuration.

Aarlo seems to need a lot of fine tuning so rather than get rid of
the options or clutter up the config flow system I'm adding a text file
where the user can configure things.

There are 2 pieces:

- `BlendedCfg`; this class is responsible for loading the new file based
  configuration and merging it with the flow data and options.

- `UpgradeCfg`; A helper class to import configuration from the old YAML
  layout.
"""

import aiofiles
import copy
import logging

import voluptuous as vol

from homeassistant.const import (
    CONF_CODE,
    CONF_HOST,
    CONF_MONITORED_CONDITIONS,
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_SCAN_INTERVAL,
    CONF_TRIGGER_TIME,
    CONF_USERNAME,
    Platform,
    UnitOfTemperature
)
from homeassistant.helpers import config_validation as cv
from homeassistant.util.yaml import parse_yaml, dump

from pyaarlo.constant import (
    AIR_QUALITY_KEY,
    ALS_STATE_KEY,
    AUDIO_DETECTED_KEY,
    BATTERY_KEY,
    BUTTON_PRESSED_KEY,
    CAPTURED_TODAY_KEY,
    CONNECTION_KEY,
    CONTACT_STATE_KEY,
    CRY_DETECTION_KEY,
    DEFAULT_AUTH_HOST,
    DEFAULT_HOST,
    HUMIDITY_KEY,
    LAST_CAPTURE_KEY,
    MOTION_DETECTED_KEY,
    MOTION_STATE_KEY,
    MQTT_HOST,
    RECENT_ACTIVITY_KEY,
    SIGNAL_STR_KEY,
    SILENT_MODE_KEY,
    TAMPER_STATE_KEY,
    TEMPERATURE_KEY,
    TOTAL_CAMERAS_KEY,
    WATER_STATE_KEY,
)

from .const import *


_LOGGER = logging.getLogger(__name__)

CONF_SIRENS = "siren"
CONF_ALL_SIRENS = "all_sirens"
CONF_SIREN_DURATION = "siren_duration"
CONF_SIREN_VOLUME = "siren_volume"
CONF_SIREN_ALLOW_OFF = "siren_allow_off"
CONF_SNAPSHOT = "snapshot"
CONF_SNAPSHOT_TIMEOUT = "snapshot_timeout"
CONF_DOORBELL_SILENCE = "doorbell_silence"

SIRENS_DEFAULT = False
SIREN_DURATION_DEFAULT = timedelta(seconds=300)
SIREN_VOLUME_DEFAULT = "8"
SIREN_ALLOW_OFF_DEFAULT = True
ALL_SIRENS_DEFAULT = False
SNAPSHOTS_DEFAULT = False
SILENT_MODE_DEFAULT = False
SNAPSHOT_TIMEOUT_DEFAULT = timedelta(seconds=60)

# This is the current aarlo main config.
AARLO_SCHEMA = vol.Schema({
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.url,
    vol.Optional(CONF_AUTH_HOST, default=DEFAULT_AUTH_HOST): cv.url,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    vol.Optional(CONF_PACKET_DUMP, default=PACKET_DUMP): cv.boolean,
    vol.Optional(CONF_CACHE_VIDEOS, default=CACHE_VIDEOS): cv.boolean,
    vol.Optional(CONF_DB_MOTION_TIME, default=DB_MOTION_TIME): cv.time_period,
    vol.Optional(CONF_DB_DING_TIME, default=DB_DING_TIME): cv.time_period,
    vol.Optional(CONF_RECENT_TIME, default=RECENT_TIME): cv.time_period,
    vol.Optional(CONF_LAST_FORMAT, default=LAST_FORMAT): cv.string,
    vol.Optional(CONF_CONF_DIR, default=CONF_DIR): cv.string,
    vol.Optional(CONF_REQ_TIMEOUT, default=REQ_TIMEOUT): cv.time_period,
    vol.Optional(CONF_STR_TIMEOUT, default=STR_TIMEOUT): cv.time_period,
    vol.Optional(CONF_NO_MEDIA_UP, default=NO_MEDIA_UP): cv.boolean,
    vol.Optional(CONF_MEDIA_RETRY, default=MEDIA_RETRY): vol.All(
        cv.ensure_list, [cv.positive_int]
    ),
    vol.Optional(CONF_SNAPSHOT_CHECKS, default=list()): vol.All(
        cv.ensure_list, [cv.positive_int]
    ),
    vol.Optional(CONF_USER_AGENT, default=USER_AGENT): cv.string,
    vol.Optional(CONF_STREAM_USER_AGENT, default=STREAM_USER_AGENT): cv.string,
    vol.Optional(CONF_MODE_API, default=MODE_API): cv.string,
    vol.Optional(CONF_DEVICE_REFRESH, default=DEVICE_REFRESH): cv.positive_int,
    vol.Optional(CONF_MODE_REFRESH, default=MODE_REFRESH): cv.positive_int,
    vol.Optional(CONF_RECONNECT_EVERY, default=RECONNECT_EVERY): cv.positive_int,
    vol.Optional(CONF_VERBOSE_DEBUG, default=VERBOSE_DEBUG): cv.boolean,
    vol.Optional(CONF_INJECTION_SERVICE, default=DEFAULT_INJECTION_SERVICE): cv.boolean,
    vol.Optional(CONF_SNAPSHOT_TIMEOUT, default=SNAPSHOT_TIMEOUT): cv.time_period,
    vol.Optional(CONF_TFA_TIMEOUT, default=DEFAULT_TFA_TIMEOUT): cv.time_period,
    vol.Optional(CONF_TFA_TOTAL_TIMEOUT, default=DEFAULT_TFA_TOTAL_TIMEOUT): cv.time_period,
    vol.Optional(CONF_LIBRARY_DAYS, default=DEFAULT_LIBRARY_DAYS): cv.positive_int,
    vol.Optional(CONF_SERIAL_IDS, default=SERIAL_IDS): cv.boolean,
    vol.Optional(CONF_STREAM_SNAPSHOT, default=STREAM_SNAPSHOT): cv.boolean,
    vol.Optional(CONF_STREAM_SNAPSHOT_STOP, default=STREAM_SNAPSHOT_STOP): cv.positive_int,
    vol.Optional(CONF_SAVE_UPDATES_TO, default=SAVE_UPDATES_TO): cv.string,
    vol.Optional(CONF_USER_STREAM_DELAY, default=USER_STREAM_DELAY): cv.positive_int,
    vol.Optional(CONF_SAVE_MEDIA_TO, default=SAVE_MEDIA_TO): cv.string,
    vol.Optional(CONF_NO_UNICODE_SQUASH, default=NO_UNICODE_SQUASH): cv.boolean,
    vol.Optional(CONF_SAVE_SESSION, default=SAVE_SESSION): cv.boolean,
    vol.Optional(CONF_BACKEND, default=DEFAULT_BACKEND): cv.string,
    vol.Optional(CONF_CIPHER_LIST, default=DEFAULT_CIPHER_LIST): cv.string,
    vol.Optional(CONF_MQTT_HOST, default=MQTT_HOST): cv.string,
    vol.Optional(CONF_MQTT_HOSTNAME_CHECK, default=DEFAULT_MQTT_HOSTNAME_CHECK): cv.boolean,
    vol.Optional(CONF_MQTT_TRANSPORT, default=DEFAULT_MQTT_TRANSPORT): cv.string,

    # Deprecated
    vol.Optional(CONF_HIDE_DEPRECATED_SERVICES, default=True): cv.boolean,
    vol.Optional(CONF_HTTP_CONNECTIONS, default=5): cv.positive_int,
    vol.Optional(CONF_HTTP_MAX_SIZE, default=10): cv.positive_int,
})

AARLO_FULL_SCHEMA = AARLO_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_TFA_SOURCE, default=DEFAULT_TFA_SOURCE): cv.string,
    vol.Optional(CONF_TFA_TYPE, default=DEFAULT_TFA_TYPE): cv.string,
    vol.Optional(CONF_TFA_HOST, default=DEFAULT_TFA_HOST): cv.string,
    vol.Optional(CONF_TFA_USERNAME, default=DEFAULT_TFA_USERNAME): cv.string,
    vol.Optional(CONF_TFA_PASSWORD, default=DEFAULT_TFA_PASSWORD): cv.string,
})

AARLO_SCHEMA_ONLY_IN_CONFIG = [
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TFA_SOURCE,
    CONF_TFA_TYPE,
    CONF_TFA_HOST,
    CONF_TFA_USERNAME,
    CONF_TFA_PASSWORD
]

AARLO_SCHEMA_DONT_SAVE = [
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TFA_SOURCE,
    CONF_TFA_TYPE,
    CONF_TFA_HOST,
    CONF_TFA_USERNAME,
    CONF_TFA_PASSWORD,
    CONF_HIDE_DEPRECATED_SERVICES,
    CONF_HTTP_CONNECTIONS,
    CONF_HTTP_MAX_SIZE,
]

# This is the default alarm schema.
ALARM_SCHEMA = vol.Schema({
    vol.Optional(CONF_CODE): cv.string,
    vol.Optional(CONF_CODE_ARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_CODE_DISARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_COMMAND_TEMPLATE, default=DEFAULT_COMMAND_TEMPLATE): cv.string,
    vol.Optional(CONF_DISARMED_MODE_NAME, default=STATE_ALARM_ARLO_DISARMED): cv.string,
    vol.Optional(CONF_HOME_MODE_NAME, default=STATE_ALARM_ARLO_HOME): cv.string,
    vol.Optional(CONF_AWAY_MODE_NAME, default=STATE_ALARM_ARLO_ARMED): cv.string,
    vol.Optional(CONF_NIGHT_MODE_NAME, default=STATE_ALARM_ARLO_NIGHT): cv.string,
    vol.Optional(CONF_ALARM_VOLUME, default=DEFAULT_ALARM_VOLUME): cv.positive_int,
    vol.Optional(CONF_TRIGGER_TIME, default=DEFAULT_TRIGGER_TIME): vol.All(
        cv.time_period, cv.positive_timedelta
    ),
})

# Binary sensor schema.
# sensor_type [ description, class, attribute, [extra_attributes], icon ]
BINARY_SENSOR_TYPES = {
    "sound": ["Sound", "sound", AUDIO_DETECTED_KEY, [], None],
    "motion": ["Motion", "motion", MOTION_DETECTED_KEY, [MOTION_STATE_KEY], None],
    "ding": ["Ding", None, BUTTON_PRESSED_KEY, [SILENT_MODE_KEY], "mdi:doorbell"],
    "cry": ["Cry", "sound", CRY_DETECTION_KEY, [], None],
    "connectivity": ["Connected", "connectivity", CONNECTION_KEY, [], None],
    "contact": ["Open/Close", "opening", CONTACT_STATE_KEY, [], None],
    "light": ["Light On", "light", ALS_STATE_KEY, [], None],
    "tamper": ["Tamper", "tamper", TAMPER_STATE_KEY, [], None],
    "leak": ["Moisture", "moisture", WATER_STATE_KEY, [], None],
}

BINARY_SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(BINARY_SENSOR_TYPES)): vol.All(
        cv.ensure_list, [vol.In(BINARY_SENSOR_TYPES)]
    ),
})

# Sensor Schema
# sensor_type [ description, unit, icon, attribute ]
SENSOR_TYPES = {
    "last_capture": ["Last", None, "run-fast", LAST_CAPTURE_KEY],
    "total_cameras": ["Arlo Cameras", None, "video", TOTAL_CAMERAS_KEY],
    "recent_activity": ["Recent Activity", None, "run-fast", RECENT_ACTIVITY_KEY],
    "captured_today": ["Captured Today", None, "file-video", CAPTURED_TODAY_KEY],
    "battery_level": ["Battery Level", "%", "battery-50", BATTERY_KEY],
    "signal_strength": ["Signal Strength", None, "signal", SIGNAL_STR_KEY],
    "temperature": ["Temperature", UnitOfTemperature.CELSIUS, "thermometer", TEMPERATURE_KEY],
    "humidity": ["Humidity", "%", "water-percent", HUMIDITY_KEY],
    "air_quality": ["Air Quality", "ppm", "biohazard", AIR_QUALITY_KEY],
}

SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
        cv.ensure_list, [vol.In(SENSOR_TYPES)]
    ),
})

# Switch schema
SWITCH_SCHEMA = vol.Schema({
    vol.Optional(CONF_SIRENS, default=SIRENS_DEFAULT): cv.boolean,
    vol.Optional(CONF_ALL_SIRENS, default=ALL_SIRENS_DEFAULT): cv.boolean,
    vol.Optional(CONF_SIREN_DURATION, default=SIREN_DURATION_DEFAULT): vol.All(
        cv.time_period, cv.positive_timedelta
    ),
    vol.Optional(CONF_SIREN_VOLUME, default=SIREN_VOLUME_DEFAULT): cv.positive_int,
    vol.Optional(CONF_SIREN_ALLOW_OFF, default=SIREN_ALLOW_OFF_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT, default=SNAPSHOTS_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT_TIMEOUT, default=SNAPSHOT_TIMEOUT_DEFAULT): vol.All(
        cv.time_period, cv.positive_timedelta
    ),
    vol.Optional(CONF_DOORBELL_SILENCE, default=SILENT_MODE_DEFAULT): cv.boolean,
})

DEFAULT_OPTIONS = {
    "alarm_control_panel_disarmed_mode_name": STATE_ALARM_ARLO_DISARMED,
    "alarm_control_panel_home_mode_name": STATE_ALARM_ARLO_HOME,
    "alarm_control_panel_away_mode_name": STATE_ALARM_ARLO_ARMED,
    "alarm_control_panel_night_mode_name": STATE_ALARM_ARLO_NIGHT,
    "alarm_control_panel_code_arm_required": False,
    "alarm_control_panel_code_disarm_required": False,
    "alarm_control_panel_trigger_time": 60,
    "alarm_control_panel_alarm_volume": 3,
    "binary_sensor_sound": True,
    "binary_sensor_motion": True,
    "binary_sensor_ding": True,
    "binary_sensor_cry": True,
    "binary_sensor_connectivity": True,
    "binary_sensor_contact": True,
    "binary_sensor_light": True,
    "binary_sensor_tamper": True,
    "binary_sensor_leak": True,
    "sensor_last_capture": True,
    "sensor_total_cameras": True,
    "sensor_recent_activity": True,
    "sensor_captured_today": True,
    "sensor_battery_level": True,
    "sensor_signal_strength": True,
    "sensor_temperature": True,
    "sensor_humidity": True,
    "sensor_air_quality": True,
    "switch_siren": True,
    "switch_all_sirens": True,
    "switch_siren_allow_off": True,
    "switch_siren_volume": 3,
    "switch_siren_duration": 10,
    "switch_snapshot": True,
    "switch_snapshot_timeout": 15,
    "switch_doorbell_silence": True
}


def _default_config_file(hass) -> str:
    return hass.config.path("aarlo.yaml")


async def _async_load_yaml(file_name):
    _LOGGER.debug("_async_load_yaml1 file_name for %s", file_name)
    try:
        async with aiofiles.open(file_name, 'r') as yaml_file:
            _LOGGER.debug("_async_load_yaml2 file_name for %s", file_name)
            contents = await yaml_file.read()
            _LOGGER.debug("_async_load_yaml3 file_name for %s", file_name)
            return parse_yaml(contents)
    except Exception as e:
        _LOGGER.debug("_async_load_yaml3 file_name for %s", file_name)
        return {}


async def _async_save_yaml(file_name, data):
    _LOGGER.debug("_async_save_yaml1 file_name for %s", file_name)
    try:
        async with aiofiles.open(file_name, 'w') as yaml_file:
            data = dump(data)
            await yaml_file.write(data)
    except Exception as e:
        _LOGGER.debug("_async_load_yaml3 file_name for %s", file_name)


def _fix_config(config):
    """Find and return the aarlo entry from any platform config.
    """
    for entry in config:
        if entry[CONF_PLATFORM] == COMPONENT_DOMAIN:
            entry = copy.deepcopy(entry)
            entry.pop(CONF_PLATFORM)
            return entry
    return {}


def _fix_value(value):
    """ If needed, convert value into a type that can be stored in yaml.
    """
    if isinstance(value, timedelta):
        return max(value.seconds, 1)
    return value


def _extract_platform_config(config_in, prefix):
    return {
        k.replace(prefix, '', 1): v for k, v in config_in.items() if k.startswith(prefix)
    }


def _extract_monitored_conditions(config_in, prefix):
    return {
        CONF_MONITORED_CONDITIONS: [k.replace(prefix, '', 1) for k, v in config_in.items() if k.startswith(prefix) and v is True]
    }


class BlendedCfg(object):
    """Helper class to get at Arlo configuration options.

    Reads in non config flow settings from the external config file and merges
    them with flow data and options.
    """

    def __init__(self, hass):
        self._hass = hass
        self._main_config = {}
        self._alarm_config = {}
        self._binary_sensor_config = {}
        self._sensor_config = {}
        self._switch_config = {}

    async def _async_load(self):
        """Load extra config from aarlo.yaml file."""

        # Read in current config
        config = await _async_load_yaml(_default_config_file(self._hass))

        # Bring in all the defaults then overwrite them. I'm trying to decouple
        # the pyaarlo config from this config.
        self._main_config = AARLO_SCHEMA({})
        self._main_config.update(config.get(COMPONENT_DOMAIN, {}))

        _LOGGER.debug(f"l-config-file={_default_config_file(self._hass)}")
        _LOGGER.debug(f"l-main-config={self._main_config}")

    def _merge(self, data, options):
        """Rebuild config from flow data and options."""

        if not options:
            _LOGGER.debug("empty options, using defaults")
            options = DEFAULT_OPTIONS

        self._main_config = {**data, **self._main_config}
        self._alarm_config = ALARM_SCHEMA(_extract_platform_config(options, "alarm_control_panel_"))
        self._binary_sensor_config = _extract_monitored_conditions(options, "binary_sensor_")
        self._sensor_config = _extract_monitored_conditions(options, "sensor_")
        self._switch_config = SWITCH_SCHEMA(_extract_platform_config(options, "switch_"))
        _LOGGER.debug(f"m-main-config={self._main_config}")
        _LOGGER.debug(f"m-alarm-config={self._alarm_config}")
        _LOGGER.debug(f"m-binary-sensor-config={self._binary_sensor_config}")
        _LOGGER.debug(f"m-sensor-config={self._sensor_config}")
        _LOGGER.debug(f"m-switch-config={self._switch_config}")

    async def async_load_and_merge(self, data, options):
        await self._async_load()
        self._merge(data, options)

    @property
    def domain_config(self):
        return self._main_config

    @property
    def alarm_config(self):
        return self._alarm_config

    @property
    def binary_sensor_config(self):
        return self._binary_sensor_config

    @property
    def sensor_config(self):
        return self._sensor_config

    @property
    def switch_config(self):
        return self._switch_config


class UpgradeCfg(object):
    """Read in the old YAML config and convert it to the new format.
    """

    @staticmethod
    async def create_file_config(hass, config):
        """ Take the current aarlo config and make the new yaml file.

        Aarlo seems to need a lot of fine tuning so rather than get rid of
        the options or clutter up the config flow system I'm adding a text file
        where the user can configure things.
        """

        _LOGGER.debug(f"new-config-file={_default_config_file(hass)}")

        # A default config.
        default_aarlo_config = AARLO_FULL_SCHEMA({
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        })

        # We need to
        # - strip out the config flow and deprecated items from this
        # - remove defaults
        # - replace timedelta with strings
        file_config = {k: _fix_value(v)
                       for k, v in config.get(COMPONENT_DOMAIN, {}).items()
                       if k not in AARLO_SCHEMA_DONT_SAVE and default_aarlo_config[k] != v}
        _LOGGER.debug(f"aarlo-file-config={file_config}")

        # For now, we move all the other configs into the options, if we need
        # to move any into the file we can read it from here.

        # Save it out.
        await _async_save_yaml(_default_config_file(hass), {
            "version": 1,
            COMPONENT_DOMAIN: file_config,
        })

    @staticmethod
    def create_flow_data(config):
        """ Take the current aarlo config and make the new flow configuration.
        """

        data = {k: v for k, v in AARLO_FULL_SCHEMA(config.get(COMPONENT_DOMAIN, {})).items()
                if k in AARLO_SCHEMA_ONLY_IN_CONFIG}

        # Add in some upgrade defaults.
        data.update({
            CONF_ADD_AARLO_PREFIX: True
        })

        _LOGGER.debug(f"aarlo-flow-data={data}")
        return data

    @staticmethod
    def create_flow_options(config):
        """ Take the current aarlo config and make the new flow options.
        """

        # Fill in the defaults, convert the time deltas and add the platform prefix.
        options = {f"alarm_control_panel_{k}": _fix_value(v)
                   for k, v in ALARM_SCHEMA(_fix_config(config.get(Platform.ALARM_CONTROL_PANEL, {}))).items()}

        # Move out of 'monitored_conditions' array and add platform prefix.
        options.update({f"binary_sensor_{v}": True
                        for v in _fix_config(config.get(Platform.BINARY_SENSOR, {})).get(CONF_MONITORED_CONDITIONS, [])})

        # Move out of 'monitored_conditions' array and add platform prefix.
        options.update({f"sensor_{v}": True
                        for v in _fix_config(config.get(Platform.SENSOR, {})).get(CONF_MONITORED_CONDITIONS, [])})

        # Fill in the defaults, convert the time deltas and add the platform prefix.
        # switch_config = SWITCH_SCHEMA(_fix_config(config.get(Platform.SWITCH, {})))
        options.update({f"switch_{k}": _fix_value(v)
                        for k, v in SWITCH_SCHEMA(_fix_config(config.get(Platform.SWITCH, {}))).items()})

        _LOGGER.debug(f"aarlo-flow-options={options}")
        return options


class PyaarloCfg(object):
    """Produce the Pyaarlo config the passed current settings.
    """

    @staticmethod
    def create_options(hass, config):

        # Copy over and convert time deltas.
        options = {k: _fix_value(v) for k, v in config.items()}

        # Fix up known naming inconsistencies. And add a needed setting.
        options.update({
            "dump": config.get(CONF_PACKET_DUMP),
            "storage_dir": config.get(CONF_CONF_DIR),

            "wait_for_initial_setup": False
        })

        # Fix up defaults.
        if options["storage_dir"] == "":
            options["storage_dir"] = hass.config.config_dir + "/.aarlo"

        _LOGGER.debug(f"config={config}")
        _LOGGER.debug(f"options={options}")

        return options
