"""
Support for Arlo Sirens.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/light
"""

import logging
from collections.abc import Callable

from homeassistant.components.siren import (
    DOMAIN as SIREN_DOMAIN,
    SirenEntity
)
from homeassistant.components.siren.const import (
    SirenEntityFeature
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from pyaarlo.constant import (
    SIREN_STATE_KEY
)

from .const import *
from .utils import to_bool


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]


async def async_setup_entry(
        hass: HomeAssistantType,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP Siren."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    # See what devices have sirens.
    all_devices = []
    for base in arlo.base_stations:
        if base.has_capability(SIREN_STATE_KEY):
            all_devices.append(base)
    for camera in arlo.cameras:
        if camera.has_capability(SIREN_STATE_KEY):
            all_devices.append(camera)
    for doorbell in arlo.doorbells:
        if doorbell.has_capability(SIREN_STATE_KEY):
            all_devices.append(doorbell)

    # We have at least one.
    if all_devices:
        sirens = []
        for device in all_devices:
            sirens.append(AarloSiren(device))

        sirens.append(AarloAllSirens(arlo, all_devices))

        async_add_entities(sirens)


class AarloSirenBase(SirenEntity):
    """Representation of an Aarlo Siren."""

    def __init__(self, sirens, name, unique_id, device_id, ):

        self._sirens = sirens

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_supported_features = SirenEntityFeature(
            SirenEntityFeature.DURATION |
            SirenEntityFeature.TURN_ON |
            SirenEntityFeature.TURN_OFF |
            SirenEntityFeature.VOLUME_SET
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        self.entity_id = f"{SIREN_DOMAIN}.{COMPONENT_DOMAIN}_{slugify(self._attr_name)}"
        _LOGGER.info(f"ArloSirenBase: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug(f"siren-callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            self._attr_is_on = any(to_bool(siren.siren_state) for siren in self._sirens)
            self.async_schedule_update_ha_state()

        for siren in self._sirens:
            _LOGGER.debug(f"register siren callbacks for {siren.name}")
            siren.add_attr_callback(SIREN_STATE_KEY, update_state)

    def turn_on(self, **kwargs):
        """Turn the sirens on."""
        volume = int(kwargs.get("volume_level", 1.0) * 8)
        duration = kwargs.get("duration", 10)
        for siren in self._sirens:
            _LOGGER.debug(f"{self._attr_name} {siren.name} vol={volume}, dur={duration}")
            siren.siren_on(duration=duration, volume=volume)

        # Flip us on. update_state should confirm this.
        self._attr_is_on = True
        self.async_schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the sirens off."""
        for siren in self._sirens:
            _LOGGER.debug(f"{self._attr_name} {siren.name} off")
            siren.siren_off()


class AarloSiren(AarloSirenBase):
    """Representation of an Aarlo Siren."""

    def __init__(self, device):

        super().__init__(
            [device],
            f"{device.name} Siren",
            f"{COMPONENT_DOMAIN}_siren_{device.device_id}",
            device.device_id
        )

        _LOGGER.info(f"ArloSiren: {self._attr_name} created")


class AarloAllSirens(AarloSirenBase):
    """Representation of an Aarlo Siren."""

    def __init__(self, arlo, devices):

        super().__init__(
            devices,
            "All Arlo Sirens",
            f"{COMPONENT_DOMAIN}_all_sirens",
            arlo.device_id
        )

        _LOGGER.info(f"ArloAllSirens: {self._attr_name} created")
