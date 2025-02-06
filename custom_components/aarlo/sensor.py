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
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify

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
    CONF_ADD_AARLO_PREFIX
)


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

# Supported Sensors
#  sensor_type: Home Assistant sensor type
#    description: What the sensor does.
#    class: Home Assistant sensor this represents
#    units: Measurement unit.
#    icon: Default ICON to use.
#    key: Pyaarlo capability that indicates this device provides this sensor
SENSOR_TYPES = {
    "last_capture": {
        "description": "Last",
        "key": LAST_CAPTURE_KEY,
        "icon": "mdi:run-fast",
    },
    "total_cameras": {
        "description": "Arlo Cameras",
        "key": TOTAL_CAMERAS_KEY,
        "icon": "mdi:video",
    },
    "recent_activity": {
        "description": "Recent Activity",
        "key": RECENT_ACTIVITY_KEY,
        "icon": "mdi:run-fast",
    },
    "captured_today": {
        "description": "Captured Today",
        "key": CAPTURED_TODAY_KEY,
        "icon": "mdi:file-video",
    },
    "battery_level": {
        "description": "Battery Level",
        "key": BATTERY_KEY,
        "class": SensorDeviceClass.BATTERY,
        "units": "%",
    },
    "signal_strength": {
        "description": "Signal Strength",
        "key": SIGNAL_STR_KEY,
        "class": SensorDeviceClass.SIGNAL_STRENGTH, 
    },
    "temperature": {
        "description": "Temperature",
        "key": TEMPERATURE_KEY,
        "class": SensorDeviceClass.TEMPERATURE,
        "units": UnitOfTemperature.CELSIUS, 
    },
    "humidity": {
        "description": "Humidity",
        "key": HUMIDITY_KEY,
        "class": SensorDeviceClass.HUMIDITY, 
        "units": "%",
    },
    "air_quality": {
        "description": "Air Quality",
        "key": AIR_QUALITY_KEY,
        "class": SensorDeviceClass.AQI,
        "units": "ppm", 
    },
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)])
})


async def async_setup_entry(
        hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP sensor."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]
    config = hass.data[COMPONENT_CONFIG][SENSOR_DOMAIN]
    _LOGGER.debug(f"sensor={config}")

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensor_value = SENSOR_TYPES[sensor_type]
        if sensor_type == "total_cameras":
            sensors.append(ArloSensor(arlo, None, aarlo_config, sensor_type, sensor_value))
        else:
            for camera in arlo.cameras:
                if camera.has_capability(sensor_value["key"]):
                    sensors.append(ArloSensor(arlo, camera, aarlo_config, sensor_type, sensor_value))
            for doorbell in arlo.doorbells:
                if doorbell.has_capability(sensor_value["key"]):
                    sensors.append(ArloSensor(arlo, doorbell, aarlo_config, sensor_type, sensor_value))
            for light in arlo.lights:
                if light.has_capability(sensor_value["key"]):
                    sensors.append(ArloSensor(arlo, light, aarlo_config, sensor_type, sensor_value))
            for sensor in arlo.sensors:
                if sensor.has_capability(sensor_value["key"]):
                    sensors.append(ArloSensor(arlo, sensor, aarlo_config, sensor_type, sensor_value))

    async_add_entities(sensors)


class ArloSensor(Entity):
    """An implementation of a Netgear Arlo IP sensor."""

    def __init__(self, arlo, device, aarlo_config, sensor_type, sensor_value):
        """Initialize an Arlo sensor."""

        self._sensor_type = sensor_type
        self._main_attr = sensor_value["key"]

        if device is None:
            self._attr_name = sensor_value["description"]
            self._attr_unique_id = sensor_type
            self._device = arlo
        else:
            self._attr_name = f"{sensor_value['description']} {device.name}"
            self._attr_unique_id = slugify(f"{sensor_value['description']}_{device.entity_id}")
            self._device = device

        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{SENSOR_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"

        self._attr_device_class = sensor_value.get("class", None)
        self._attr_icon = sensor_value.get("icon", None)
        self._attr_unit_of_measurement = sensor_value.get("units", None)
        self._attr_should_poll = False
        self._attr_state = None

        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"ArloSensor: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug("callback:" + self._attr_name + ":" + attr + ":" + str(value)[:80])
            self._attr_state = value
            self.schedule_update_ha_state()

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
