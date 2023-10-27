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

import copy
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_CODE,
    CONF_HOST,
    CONF_MONITORED_CONDITIONS,
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_SCAN_INTERVAL,
    CONF_TRIGGER_TIME,
    CONF_USERNAME,
    Platform,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    TEMP_CELSIUS,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.util.yaml import load_yaml, save_yaml

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

ARMED = "armed"
DISARMED = "disarmed"

CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_CODE_DISARM_REQUIRED = "code_disarm_required"
CONF_DISARMED_MODE_NAME = "disarmed_mode_name"
CONF_HOME_MODE_NAME = "home_mode_name"
CONF_AWAY_MODE_NAME = "away_mode_name"
CONF_NIGHT_MODE_NAME = "night_mode_name"
CONF_ALARM_VOLUME = "alarm_volume"
CONF_COMMAND_TEMPLATE = "command_template"
CONF_SIRENS = "siren"
CONF_ALL_SIRENS = "all_sirens"
CONF_SIREN_DURATION = "siren_duration"
CONF_SIREN_VOLUME = "siren_volume"
CONF_SIREN_ALLOW_OFF = "siren_allow_off"
CONF_SNAPSHOT = "snapshot"
CONF_SNAPSHOT_TIMEOUT = "snapshot_timeout"
CONF_DOORBELL_SILENCE = "doorbell_silence"

DEFAULT_COMMAND_TEMPLATE = "{{action}}"
DEFAULT_TRIGGER_TIME = timedelta(seconds=60)
DEFAULT_HOME = "home"
DEFAULT_NIGHT = "night"
DEFAULT_ALARM_VOLUME = "8"
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

# This is the default alarm schema.
ALARM_SCHEMA = vol.Schema({
    vol.Optional(CONF_CODE): cv.string,
    vol.Optional(CONF_CODE_ARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_CODE_DISARM_REQUIRED, default=True): cv.boolean,
    vol.Optional(CONF_COMMAND_TEMPLATE, default=DEFAULT_COMMAND_TEMPLATE): cv.string,
    vol.Optional(CONF_DISARMED_MODE_NAME, default=DISARMED): cv.string,
    vol.Optional(CONF_HOME_MODE_NAME, default=DEFAULT_HOME): cv.string,
    vol.Optional(CONF_AWAY_MODE_NAME, default=ARMED): cv.string,
    vol.Optional(CONF_NIGHT_MODE_NAME, default=DEFAULT_NIGHT): cv.string,
    vol.Optional(CONF_ALARM_VOLUME, default=DEFAULT_ALARM_VOLUME): cv.string,
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
    "temperature": ["Temperature", TEMP_CELSIUS, "thermometer", TEMPERATURE_KEY],
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
    vol.Optional(CONF_SIREN_VOLUME, default=SIREN_VOLUME_DEFAULT): cv.string,
    vol.Optional(CONF_SIREN_ALLOW_OFF, default=SIREN_ALLOW_OFF_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT, default=SNAPSHOTS_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT_TIMEOUT, default=SNAPSHOT_TIMEOUT_DEFAULT): vol.All(
        cv.time_period, cv.positive_timedelta
    ),
    vol.Optional(CONF_DOORBELL_SILENCE, default=SILENT_MODE_DEFAULT): cv.boolean,
})

AARLO_CONFIG_FILE = "/config/aarlo.yaml"


def _fix_config(config):
    """Find and return the aarlo entry from any platform config.
    """
    for entry in config:
        if entry[CONF_PLATFORM] == DOMAIN:
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

    _main_config = {}
    _alarm_config = {}
    _binary_sensor_config = {}
    _sensor_config = {}
    _switch_config = {}

    def __init__(self, data, options):
        self.load()
        self.merge(data, options)

    def load(self):
        """ Load extra config from aarlo.yaml file.
        """

        # Read in current config
        config = {}
        try:
            config = load_yaml(AARLO_CONFIG_FILE)
        except Exception as e:
            _LOGGER.debug(f"failed to read aarlo config {str(e)}")

        # Fix up the pieces to standard defaults..
        self._main_config = AARLO_SCHEMA(config.get(DOMAIN, {}))

        _LOGGER.debug(f"l-config-file={AARLO_CONFIG_FILE}")
        _LOGGER.debug(f"l-main-config={self._main_config}")

    def merge(self, data, options):
        """ Rebuild config from flow data and options.
        """

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
    def create_file_config(config):
        """ Take the current aarlo config and make the new yaml file.

        Aarlo seems to need a lot of fine tuning so rather than get rid of
        the options or clutter up the config flow system I'm adding a text file
        where the user can configure things.
        """

        # A default config.
        default_aarlo_config = AARLO_FULL_SCHEMA({
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        })

        # We need to
        # - strip out the config flow items from this
        # - remove defaults
        # - replace timedelta with strings
        file_config = {k: _fix_value(v)
                       for k, v in config.get(DOMAIN, {}).items()
                       if k not in AARLO_SCHEMA_ONLY_IN_CONFIG and default_aarlo_config[k] != v}
        _LOGGER.debug(f"aarlo-file-config={file_config}")

        # For now, we move all the other configs into the options, if we need
        # to move any into the file we can read it from here.

        # Save it out.
        try:
            save_yaml(AARLO_CONFIG_FILE, {
                "version": 1,
                DOMAIN: file_config,
            })
        except Exception as e:
            _LOGGER.debug(f"couldn't save user data {str(e)}")

    @staticmethod
    def create_flow_data(config):
        """ Take the current aarlo config and make the new flow configuration.
        """

        data = {k: v for k, v in AARLO_FULL_SCHEMA(config.get(DOMAIN, {})).items()
                if k in AARLO_SCHEMA_ONLY_IN_CONFIG }

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
