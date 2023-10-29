"""
Support for Arlo Lights.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/light
"""

import logging
import pprint
from collections.abc import Callable

import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from pyaarlo.constant import (
    BRIGHTNESS_KEY,
    FLOODLIGHT_KEY,
    LAMP_STATE_KEY,
    LIGHT_BRIGHTNESS_KEY,
    LIGHT_MODE_KEY,
    NIGHTLIGHT_KEY,
    SPOTLIGHT_BRIGHTNESS_KEY,
    SPOTLIGHT_KEY,
)

from . import to_bool
from .const import (
    ATTR_BATTERY_TECH,
    ATTR_CHARGER_TYPE,
    COMPONENT_ATTRIBUTION,
    COMPONENT_BRAND,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
)


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

LIGHT_EFFECT_RAINBOW = "rainbow"
LIGHT_EFFECT_NONE = "none"


async def async_setup_entry(
        hass: HomeAssistantType,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP light."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    lights = []
    for light in arlo.lights:
        lights.append(ArloLight(light))
    for camera in arlo.cameras:
        if camera.has_capability(NIGHTLIGHT_KEY):
            lights.append(ArloNightLight(camera))
        if camera.has_capability(FLOODLIGHT_KEY):
            lights.append(ArloFloodLight(camera))
        if camera.has_capability(SPOTLIGHT_KEY):
            lights.append(ArloSpotlight(camera))

    async_add_entities(lights)


class ArloLight(LightEntity):

    def __init__(self, light):
        """Initialize an Arlo light."""

        self._light = light

        self._attr_name = light.name
        self._attr_unique_id = light.entity_id

        self._attr_brightness = None
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._light.device_id)},
            manufacturer=COMPONENT_BRAND,
        )
        
        _LOGGER.info(f"ArloLight: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_light, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:attr:{str(value)[:80]}")
            if attr == LAMP_STATE_KEY:
                self._attr_is_on = to_bool(value)
            if attr == BRIGHTNESS_KEY:
                self._attr_brightness = value
            self.async_schedule_update_ha_state()

        self._attr_is_on = to_bool(self._light.attribute(LAMP_STATE_KEY, default="off"))
        self._attr_brightness = self._light.attribute(BRIGHTNESS_KEY, default=255)
        _LOGGER.debug(f"initial setting on={self._attr_is_on}, bright={self._attr_brightness}")

        self._light.add_attr_callback(LAMP_STATE_KEY, update_state)
        self._light.add_attr_callback(BRIGHTNESS_KEY, update_state)

    def turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug(f"turning on {self._attr_name} (with args {pprint.pformat(kwargs)})")

        rgb = kwargs.get(ATTR_HS_COLOR, None)
        if rgb is not None:
            rgb = color_util.color_hs_to_RGB(*rgb)
        brightness = kwargs.get(ATTR_BRIGHTNESS, None)

        self._light.turn_on(brightness=brightness, rgb=rgb)
        self._attr_is_on = True

    def turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug(f"turning off {self._attr_name} (with args {pprint.pformat(kwargs)})")
        self._light.turn_off()
        self._attr_is_on = False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""

        attrs = {
            name: value
            for name, value in (
                (ATTR_BATTERY_LEVEL, self._light.battery_level),
                (ATTR_BATTERY_TECH, self._light.battery_tech),
                (ATTR_BATTERY_CHARGING, self._light.is_charging),
                (ATTR_CHARGER_TYPE, self._light.charger_type),
                (BRIGHTNESS_KEY, self._attr_brightness),
            )
            if value is not None
        }

        attrs.update({
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "device_brand": COMPONENT_BRAND,
            "device_id": self._light.device_id,
            "device_model": self._light.model_id,
        })

        return attrs


class ArloNightLight(ArloLight):
    def __init__(self, camera):
        super().__init__(camera)

        self._attr_brightness = None
        self._attr_color_temp = None
        self._attr_effect = None
        self._attr_effect_list = [LIGHT_EFFECT_NONE, LIGHT_EFFECT_RAINBOW]
        self._attr_hs_color = None
        self._attr_max_mireds = color_util.color_temperature_kelvin_to_mired(9000)
        self._attr_min_mireds = color_util.color_temperature_kelvin_to_mired(2500)
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.HS
        }
        self._attr_supported_features = LightEntityFeature(
            LightEntityFeature.EFFECT
        )

        _LOGGER.info(f"ArloNightLight: {self._attr_name} created")

    def _set_light_mode(self, light_mode):
        _LOGGER.debug(f"ArloNightLight: {self._attr_name} light mode {light_mode}")
        if light_mode is None:
            return

        # {'mode': 'rgb', 'rgb': {'red': 118, 'green': 255, 'blue': 91}}
        # {'mode': 'temperature', 'temperature': 2650}
        # {'mode': 'rainbow'}
        mode = light_mode.get("mode")
        if mode is None:
            return

        if mode == "rgb":
            rgb = light_mode.get("rgb")
            self._attr_hs_color = color_util.color_RGB_to_hs(
                rgb.get("red"), rgb.get("green"), rgb.get("blue")
            )
            self._attr_effect = LIGHT_EFFECT_NONE
        elif mode == "temperature":
            temperature = light_mode.get("temperature")
            self._attr_color_temp = color_util.color_temperature_kelvin_to_mired(temperature)
            self._attr_hs_color = color_util.color_temperature_to_hs(temperature)
            self._attr_effect = LIGHT_EFFECT_NONE
        elif mode == LIGHT_EFFECT_RAINBOW:
            self._attr_effect = LIGHT_EFFECT_RAINBOW

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_attr(_light, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            if attr == LIGHT_BRIGHTNESS_KEY:
                self._attr_brightness = value
            if attr == LIGHT_MODE_KEY:
                self._set_light_mode(value)
            self.async_schedule_update_ha_state()

        self._attr_brightness = self._light.attribute(LIGHT_BRIGHTNESS_KEY, default=255)
        self._set_light_mode(self._light.attribute(LIGHT_MODE_KEY))

        self._light.add_attr_callback(LIGHT_BRIGHTNESS_KEY, update_attr)
        self._light.add_attr_callback(LIGHT_MODE_KEY, update_attr)
        await super().async_added_to_hass()

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug(f"turning on {self._attr_name} (with args {pprint.pformat(kwargs)})")

        self._light.nightlight_on()
        if ATTR_BRIGHTNESS in kwargs:
            self._light.set_nightlight_brightness(kwargs[ATTR_BRIGHTNESS])

        if ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._light.set_nightlight_rgb(red=rgb[0], green=rgb[1], blue=rgb[2])

        if ATTR_COLOR_TEMP in kwargs:
            kelvin = color_util.color_temperature_mired_to_kelvin(
                kwargs.get(ATTR_COLOR_TEMP)
            )
            self._light.set_nightlight_color_temperature(kelvin)

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            if effect == LIGHT_EFFECT_RAINBOW:
                self._light.set_nightlight_mode("rainbow")
            else:
                self._light.set_nightlight_mode("rgb")

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug(f"turning off {self._attr_name} (with args {pprint.pformat(kwargs)})")
        self._light.nightlight_off()


class ArloFloodLight(ArloLight):
    def __init__(self, camera):
        super().__init__(camera)

        self._mode = None
        self._duration = None
        self._als_sensitivity = None

        self._sleep_time = None
        self._sleep_time_rel = None

        self._attr_brightness = None
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS
        }

        _LOGGER.info(f"ArloFloodLight: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        def set_states(state):
            if "on" in state:
                self._attr_is_on = True if state.get("on") else False
            if "brightness1" in state:
                self._attr_brightness = int(state.get("brightness1") / 100.0 * 255)
            if "behavior" in state:
                self._mode = state.get("behavior")
            if "alsSensitivity" in state:
                self._als_sensitivity = state.get("alsSensitivity")
            if "duration" in state:
                self._duration = state.get("duration")
            if self._attr_is_on:
                if "sleepTime" in state:
                    self._sleep_time = state.get("sleepTime")
                if "sleepTimeRel" in state:
                    self._sleep_time_rel = state.get("sleepTimeRel")
            else:
                self._sleep_time = None
                self._sleep_time_rel = None

        @callback
        def update_attr(_light, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            set_states(value)
            self.async_schedule_update_ha_state()

        floodlight = self._light.attribute(FLOODLIGHT_KEY, default={})
        set_states(floodlight)

        self._light.add_attr_callback(FLOODLIGHT_KEY, update_attr)

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug(f"turning on {self._attr_name} (with args {pprint.pformat(kwargs)})")

        self._light.floodlight_on()
        if ATTR_BRIGHTNESS in kwargs:
            self._light.set_floodlight_brightness(kwargs[ATTR_BRIGHTNESS])

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug(f"turning off {self._attr_name} (with args {pprint.pformat(kwargs)})")
        self._light.floodlight_off()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""

        super_attrs = super().extra_state_attributes
        flood_attrs = {
            name: value
            for name, value in (
                ("duration", self._duration),
                ("sleep_time_rel", self._sleep_time_rel),
                ("sleep_time", self._sleep_time),
                ("mode", self._mode),
                ("als_sensitivity", self._als_sensitivity),
            )
            if value is not None
        }

        attrs = dict()
        attrs.update(super_attrs)
        attrs.update(flood_attrs)

        return attrs


class ArloSpotlight(ArloLight):

    def __init__(self, camera):
        super().__init__(camera)

        self._attr_brightness = None
        self._attr_effect = None
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS
        }
        self._attr_supported_features = LightEntityFeature(
            LightEntityFeature.EFFECT
        )

        _LOGGER.info(f"ArloSpotlight: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_attr(_light, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            if attr == SPOTLIGHT_KEY:
                self._attr_is_on = to_bool(value)
            if attr == SPOTLIGHT_BRIGHTNESS_KEY:
                self._attr_brightness = value / 100 * 255
            self.async_schedule_update_ha_state()

        self._attr_is_on = to_bool(self._light.attribute(SPOTLIGHT_KEY, default="off"))
        self._attr_brightness = self._light.attribute(SPOTLIGHT_BRIGHTNESS_KEY, default=255)

        self._light.add_attr_callback(SPOTLIGHT_KEY, update_attr)
        self._light.add_attr_callback(SPOTLIGHT_BRIGHTNESS_KEY, update_attr)
        await super().async_added_to_hass()

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug(f"turning on {self._attr_name} (with args {pprint.pformat(kwargs)})")

        self._light.set_spotlight_on()
        if ATTR_BRIGHTNESS in kwargs:
            self._light.set_spotlight_brightness(kwargs[ATTR_BRIGHTNESS])

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug(f"turning off {self._attr_name} (with args {pprint.pformat(kwargs)})")
        self._light.set_spotlight_off()
