"""
Support for Arlo Sensors.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/sensor
"""

import logging
import voluptuous as vol
from collections.abc import Callable

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_MONITORED_CONDITIONS,
    TEMP_CELSIUS,
)
from homeassistant.core import callback
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from pyaarlo.constant import (
    AIR_QUALITY_KEY,
    BATTERY_KEY,
    CAPTURED_TODAY_KEY,
    HUMIDITY_KEY,
    LAST_CAPTURE_KEY,
    RECENT_ACTIVITY_KEY,
    SIGNAL_STR_KEY,
    TEMPERATURE_KEY,
    TOTAL_CAMERAS_KEY,
)

from .const import (
    COMPONENT_ATTRIBUTION,
    COMPONENT_BRAND,
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
)


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

# Supported Sensors
#  sensor_type: Home Assistant sensor type
#    description: What the sensor does.
#    class: Home Assistant sensor this represents
#    unit: Measurement unit.
#    icon: Default ICON to use.
#    attribute: Pyaarlo capability that indicates this device provides this sensor
# sensor_type [ description, unit, icon, attribute ]
SENSOR_TYPES_DESCRIPTION = 0
SENSOR_TYPES_CLASS = 1
SENSOR_TYPES_UNIT = 2
SENSOR_TYPES_ICON = 3
SENSOR_TYPES_MAIN_ATTR = 4
SENSOR_TYPES = {
    "last_capture": ["Last", None, None, "run-fast", LAST_CAPTURE_KEY],
    "total_cameras": ["Arlo Cameras", None, None, "video", TOTAL_CAMERAS_KEY],
    "recent_activity": ["Recent Activity", None, None, "run-fast", RECENT_ACTIVITY_KEY],
    "captured_today": ["Captured Today", None, None, "file-video", CAPTURED_TODAY_KEY],
    "battery_level": ["Battery Level", SensorDeviceClass.BATTERY, "%", "battery-50", BATTERY_KEY],
    "signal_strength": ["Signal Strength", None, None, "signal", SIGNAL_STR_KEY],
    "temperature": ["Temperature", SensorDeviceClass.TEMPERATURE, TEMP_CELSIUS, "thermometer", TEMPERATURE_KEY],
    "humidity": ["Humidity", SensorDeviceClass.HUMIDITY, "%", "water-percent", HUMIDITY_KEY],
    "air_quality": ["Air Quality", SensorDeviceClass.AQI, "ppm", "biohazard", AIR_QUALITY_KEY],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)])
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

    config = hass.data[COMPONENT_CONFIG][SENSOR_DOMAIN]
    _LOGGER.debug(f"sensor={config}")

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensor_value = SENSOR_TYPES[sensor_type]
        if sensor_type == "total_cameras":
            sensors.append(ArloSensor(arlo, None, sensor_type, sensor_value))
        else:
            for camera in arlo.cameras:
                if camera.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                    sensors.append(ArloSensor(arlo, camera, sensor_type, sensor_value))
            for doorbell in arlo.doorbells:
                if doorbell.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                    sensors.append(ArloSensor(arlo, doorbell, sensor_type, sensor_value))
            for light in arlo.lights:
                if light.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                    sensors.append(ArloSensor(arlo, light, sensor_type, sensor_value))
            for sensor in arlo.sensors:
                if sensor.has_capability(sensor_value[SENSOR_TYPES_MAIN_ATTR]):
                    sensors.append(ArloSensor(arlo, sensor, sensor_type, sensor_value))

    async_add_entities(sensors)


class ArloSensor(Entity):
    """An implementation of a Netgear Arlo IP sensor."""

    def __init__(self, arlo, device, sensor_type, sensor_value):
        """Initialize an Arlo sensor."""

        self._sensor_type = sensor_type
        self._main_attr = sensor_value[SENSOR_TYPES_MAIN_ATTR]

        if device is None:
            self._attr_name = sensor_value[SENSOR_TYPES_DESCRIPTION]
            self._attr_unique_id = sensor_type
            self._device = arlo
        else:
            self._attr_name = "{0} {1}".format(sensor_value[SENSOR_TYPES_DESCRIPTION], device.name)
            self._attr_unique_id = (
                "{0}_{1}".format(sensor_value[SENSOR_TYPES_DESCRIPTION], device.entity_id)
                .lower()
                .replace(" ", "_")
            )
            self._device = device

        self._attr_device_class = sensor_value[SENSOR_TYPES_CLASS]
        self._attr_icon = f"mdi:{sensor_value[SENSOR_TYPES_ICON]}"
        self._attr_should_poll = False
        self._attr_state = None
        self._attr_unit_of_measurement = sensor_value[SENSOR_TYPES_UNIT]
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"ArloSensor: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug("callback:" + self._attr_name + ":" + attr + ":" + str(value)[:80])
            self._attr_state = value
            self.async_schedule_update_ha_state()

        if self._main_attr is not None:
            self._attr_state = self._device.attribute(self._main_attr)
            self._device.add_attr_callback(self._main_attr, update_state)

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

        # XXX maybe be better as sensor
        if self._sensor_type == "last_capture":
            video = self._device.last_video_url
            if video is not None:
                attrs["video_url"] = video
                attrs["thumbnail_url"] = self._device.last_video_thumbnail_url
                attrs["object_type"] = self._device.last_video_object_type
                attrs["object_region"] = self._device.last_video_object_region
            else:
                attrs["object_type"] = None

        return attrs
