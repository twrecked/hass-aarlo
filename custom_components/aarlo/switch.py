"""
Support for Arlo Switches.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/switch/
"""

import logging
from collections.abc import Callable
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify
from .utils import get_entity_identifiers

from pyaarlo.constant import (
    ACTIVITY_STATE_KEY,
    SILENT_MODE_KEY
)

from .const import *
from .utils import to_bool


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_SIRENS, default=SIRENS_DEFAULT): cv.boolean,
    vol.Optional(CONF_ALL_SIRENS, default=ALL_SIRENS_DEFAULT): cv.boolean,
    vol.Optional(CONF_SIREN_DURATION, default=SIREN_DURATION_DEFAULT):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_SIREN_VOLUME, default=SIREN_VOLUME_DEFAULT): cv.string,
    vol.Optional(CONF_SIREN_ALLOW_OFF, default=SIREN_ALLOW_OFF_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT, default=SNAPSHOTS_DEFAULT): cv.boolean,
    vol.Optional(CONF_SNAPSHOT_TIMEOUT, default=SNAPSHOT_TIMEOUT_DEFAULT):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DOORBELL_SILENCE, default=SILENT_MODE_DEFAULT): cv.boolean,
})


async def async_setup_entry(
        hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None]
) -> None:

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]
    config = hass.data[COMPONENT_CONFIG][SWITCH_DOMAIN]
    _LOGGER.debug(f"switch={config}")

    devices: list[SwitchEntity] = []

    # Add snapshot for each camera
    if config.get(CONF_SNAPSHOT) is True:
        for camera in arlo.cameras:
            devices.append(AarloSnapshotSwitch(aarlo_config, config, camera))

    if config.get(CONF_DOORBELL_SILENCE) is True:
        for doorbell in arlo.doorbells:
            if doorbell.has_capability(SILENT_MODE_KEY):
                devices.append(AarloSilentModeSwitch(aarlo_config, doorbell))
                devices.append(AarloSilentModeChimeSwitch(aarlo_config, doorbell))
                devices.append(AarloSilentModeCallSwitch(aarlo_config, doorbell))

    async_add_entities(devices)


class AarloSwitch(SwitchEntity):
    """Representation of an Aarlo switch."""

    _attr_suggested_object_id: str | None = None

    @property
    def suggested_object_id(self) -> str | None:
        return self._attr_suggested_object_id

    @suggested_object_id.setter
    def suggested_object_id(self, value: str | None) -> None:
        self._attr_suggested_object_id = value

    def __init__(self, device, aarlo_config, name, identifier, icon):
        """Initialize the Aarlo switch device."""
        
        self._device = device

        self._attr_has_entity_name = True
        self._attr_name = name
        if identifier is not None:
            prefix = "aarlo_" if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True) else ""
            self._attr_unique_id = slugify(identifier)
            self.suggested_object_id = f"{prefix}{self._attr_unique_id}"
        else:
            self._attr_unique_id, self.suggested_object_id = get_entity_identifiers(
                aarlo_config, device, name
            )
        self.entity_id = f"{SWITCH_DOMAIN}.{self.suggested_object_id}"

        self._attr_icon = f"mdi:{icon}"
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"AarloSwitch: {self.name} created")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("implement turn on")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("implement turn off")

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        return {
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self.name,
            "device_brand": COMPONENT_BRAND,
            "device_name": self._device.name,
            "device_id": self._device.device_id,
            "device_model": self._device.model_id,
        }


class AarloSnapshotSwitch(AarloSwitch):
    """Representation of an Aarlo switch."""

    def __init__(self, aarlo_config, config, camera):
        """Initialize the Aarlo snapshot switch device."""
        super().__init__(
            camera, aarlo_config,
            "Snapshot",
            None,
            "camera",
        )

        self._timeout = config.get(CONF_SNAPSHOT_TIMEOUT)

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug(f"snapshot-callback:{self.name}:{attr}:{str(value)[:80]}")
            # XXX beef this check up in pyaarlo; idle == not taking a snapshot
            # self._attr_is_on = self._device.is_taking_snapshot
            self._attr_is_on = "snapshot" in value.lower()
            self.schedule_update_ha_state()

        self._device.add_attr_callback(ACTIVITY_STATE_KEY, update_state)

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug(f"starting snapshot for {self.name}")
        if not self._device.is_taking_snapshot:
            await self._device.request_snapshot()
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug(f"cancelling snapshot for {self.name}")
        if self._device.is_taking_snapshot:
            await self._device.stop_activity()
            self._attr_is_on = False
            self.async_write_ha_state()


class AarloSilentModeBaseSwitch(AarloSwitch):
    """Representation of an Aarlo Doorbell Silence switch."""

    _block: str = "all"

    def __init__(self, aarlo_config, name, identifier, doorbell, block):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(doorbell, aarlo_config, name, identifier, "doorbell")

        self._block = block

    async def async_turn_off(self, **kwargs):
        # XXX pyaarlo needs looking at to stop traditional chimes
        _LOGGER.debug(f"Turning off silent mode for {self.name}")
        await self._device.silence_off()
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug(f"callback:{self.name}:{attr}:{str(value)[:100]}")
            if self._block == "calls":
                self._attr_is_on = self._device.calls_are_silenced
            elif self._block == "chimes":
                self._attr_is_on = self._device.chimes_are_silenced
            else:
                self._attr_is_on = self._device.is_silenced
            self.schedule_update_ha_state()

        self._device.add_attr_callback(SILENT_MODE_KEY, update_state)


class AarloSilentModeSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence chimes and calls.

    This switch will mute everything!
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            "Silent Mode Chime Call",
            f"{doorbell.entity_id}_silent_mode_chime_call",
            doorbell,
            block="all",
        )

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent mode for {self.name}")
        await self._device.silence_on()
        self._attr_is_on = True
        self.async_write_ha_state()


class AarloSilentModeChimeSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence chimes.

    This switch will mute just chimes.
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            "Silent Mode Chime",
            f"{doorbell.entity_id}_silent_mode_chime",
            doorbell,
            block="chimes",
        )

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent chimes mode for {self.name}")
        await self._device.silence_chimes()
        self._attr_is_on = True
        self.async_write_ha_state()


class AarloSilentModeCallSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence calls.

    This switch will mute just calls.
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            "Silent Mode Call",
            f"{doorbell.entity_id}_silent_mode_call",
            doorbell,
            block="calls",
        )

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent calls mode for {self.name}")
        await self._device.silence_calls()
        self._attr_is_on = True
        self.async_write_ha_state()
