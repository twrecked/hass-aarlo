"""
Support for Arlo Binary Sensors.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/binary_sensor
"""

import logging
import voluptuous as vol
from collections.abc import Callable

import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    DOMAIN as BINARY_SENSOR_DOMAIN
)
from homeassistant.const import ATTR_ATTRIBUTION, CONF_MONITORED_CONDITIONS
from homeassistant.core import callback
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from pyaarlo.constant import (
    ALS_STATE_KEY,
    AUDIO_DETECTED_KEY,
    BUTTON_PRESSED_KEY,
    CONNECTION_KEY,
    CONTACT_STATE_KEY,
    CRY_DETECTION_KEY,
    MOTION_DETECTED_KEY,
    MOTION_STATE_KEY,
    SILENT_MODE_KEY,
    TAMPER_STATE_KEY,
    WATER_STATE_KEY,
)

from . import (
    COMPONENT_ATTRIBUTION,
    COMPONENT_BRAND,
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
    CONF_ADD_AARLO_PREFIX
)
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

# Supported Sensors
#  sensor_type: Home Assistant sensor type
#    description: What the sensor does.
#    class: Home Assistant sensor this represents
#    main attribute: Pyaarlo capability that indicates this device provides this sensor
#    extra_attributes: Another attributes to watch for this sensor
#    icon: Default ICON to use.
SENSOR_TYPES_DESCRIPTION = 0
SENSOR_TYPES_CLASS = 1
SENSOR_TYPES_MAIN_ATTR = 2
SENSOR_TYPES_OTHER_ATTRS = 3
SENSOR_TYPES_ICON = 4
SENSOR_TYPES = {
    "sound": ["Sound", BinarySensorDeviceClass.SOUND, AUDIO_DETECTED_KEY, [], None],
    "motion": ["Motion", BinarySensorDeviceClass.MOTION, MOTION_DETECTED_KEY, [MOTION_STATE_KEY], None],
    "ding": ["Ding", None, BUTTON_PRESSED_KEY, [SILENT_MODE_KEY], "mdi:doorbell"],
    "cry": ["Cry", BinarySensorDeviceClass.SOUND, CRY_DETECTION_KEY, [], None],
    "connectivity": ["Connected", BinarySensorDeviceClass.CONNECTIVITY, CONNECTION_KEY, [], None],
    "contact": ["Open/Close", BinarySensorDeviceClass.OPENING, CONTACT_STATE_KEY, [], None],
    "light": ["Light On", BinarySensorDeviceClass.LIGHT, ALS_STATE_KEY, [], None],
    "tamper": ["Tamper", BinarySensorDeviceClass.TAMPER, TAMPER_STATE_KEY, [], None],
    "leak": ["Moisture", BinarySensorDeviceClass.MOISTURE, WATER_STATE_KEY, [], None],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


async def async_setup_entry(
        hass: HomeAssistantType,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP sensor."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]
    config = hass.data[COMPONENT_CONFIG][BINARY_SENSOR_DOMAIN]
    _LOGGER.debug(f"binary-sensor={config}")

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensor_value = SENSOR_TYPES[sensor_type]
        if sensor_type == "connectivity":
            for base in arlo.base_stations:
                if base.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                    sensors.append(ArloBinarySensor(base, aarlo_config, sensor_type, sensor_value))
        for camera in arlo.cameras:
            if camera.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                sensors.append(ArloBinarySensor(camera, aarlo_config, sensor_type, sensor_value))
        for doorbell in arlo.doorbells:
            if doorbell.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                sensors.append(ArloBinarySensor(doorbell, aarlo_config, sensor_type, sensor_value))
        for light in arlo.lights:
            if light.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                sensors.append(ArloBinarySensor(light, aarlo_config, sensor_type, sensor_value))
        for sensor in arlo.sensors:
            if sensor.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                sensors.append(ArloBinarySensor(sensor, aarlo_config, sensor_type, sensor_value))

    async_add_entities(sensors)


class ArloBinarySensor(BinarySensorEntity):
    """An implementation of a Netgear Arlo IP sensor."""

    def __init__(self, device, aarlo_config, sensor_type, sensor_value):
        """Initialize an Arlo sensor."""

        self._device = device
        self._sensor_type = sensor_type
        self._main_attr = sensor_value[SENSOR_TYPES_MAIN_ATTR]
        self._other_attrs = sensor_value[SENSOR_TYPES_OTHER_ATTRS]

        self._attr_name = f"{sensor_value[SENSOR_TYPES_DESCRIPTION]} {device.name}"
        self._attr_unique_id = f"{sensor_value[SENSOR_TYPES_DESCRIPTION]}_{device.entity_id}"
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{BINARY_SENSOR_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"
        _LOGGER.debug(f"binary-sensor-entity-id={self.entity_id}")

        self._attr_icon = sensor_value[SENSOR_TYPES_ICON]
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_device_class = sensor_value[SENSOR_TYPES_CLASS]
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"ArloBinarySensor: {self._attr_name} created")

    def _map_value(self, attr, value):
        if attr == CONNECTION_KEY:
            value = True if value == "available" else False
        return value

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug("callback:" + self._attr_name + ":" + attr + ":" + str(value)[:80])
            if self._main_attr == attr:
                self._attr_is_on = self._map_value(attr, value)
            self.async_schedule_update_ha_state()

        if self._main_attr is not None:
            self._attr_is_on = self._map_value(self._main_attr, self._device.attribute(self._main_attr))
            self._device.add_attr_callback(self._main_attr, update_state)
        for other_attr in self._other_attrs:
            self._device.add_attr_callback(other_attr, update_state)

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "device_brand": COMPONENT_BRAND,
            "device_name": self._device.name,
            "device_id": self._device.device_id,
            "device_model": self._device.model_id,
        }
        if self._sensor_type == "ding":
            attrs.update({
                "chimes_silenced": self._device.chimes_are_silenced,
                "calls_silenced": self._device.calls_are_silenced
            })
        return attrs

