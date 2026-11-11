"""
Support for Arlo Sirens.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/light
"""

import asyncio
import logging
from collections.abc import Callable

from homeassistant.components.siren import (
    DOMAIN as SIREN_DOMAIN,
    SirenEntity
)
from homeassistant.components.siren.const import (
    SirenEntityFeature
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify

from pyaarlo.constant import (
    SIREN_STATE_KEY
)

from .const import *
from .utils import to_bool


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]


async def async_setup_entry(
        hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP Siren."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    # See what devices have sirens (deduplicating cameras that are their own base stations).
    all_devices = []
    seen_ids = set()
    for dev in (*arlo.base_stations, *arlo.cameras, *arlo.doorbells):
        if dev.device_id not in seen_ids and dev.has_capability(SIREN_STATE_KEY):
            seen_ids.add(dev.device_id)
            all_devices.append(dev)

    # We have at least one.
    if all_devices:
        sirens: list[SirenEntity] = []
        for device in all_devices:
            sirens.append(AarloSiren(device))

        sirens.append(AarloAllSirens(arlo, all_devices))

        async_add_entities(sirens)


class AarloSirenBase(SirenEntity):
    """Representation of an Aarlo Siren."""

    _attr_suggested_object_id: str | None = None

    @property
    def suggested_object_id(self) -> str | None:
        return self._attr_suggested_object_id

    @suggested_object_id.setter
    def suggested_object_id(self, value: str | None) -> None:
        self._attr_suggested_object_id = value

    def __init__(self, sirens, name, unique_id, device_id, suggested_object_id=None, has_entity_name=True):

        self._sirens = sirens

        self._attr_has_entity_name = has_entity_name
        self._attr_name = name
        self._attr_unique_id = unique_id
        if suggested_object_id:
            self.suggested_object_id = suggested_object_id
            self.entity_id = f"{SIREN_DOMAIN}.{self.suggested_object_id}"
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

        _LOGGER.info(f"ArloSirenBase: {self.name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug(f"siren-callback:{self.name}:{attr}:{str(value)[:80]}")
            self._attr_is_on = any(to_bool(siren.siren_state) for siren in self._sirens)
            self.schedule_update_ha_state()

        for siren in self._sirens:
            _LOGGER.debug(f"register siren callbacks for {siren.name}")
            siren.add_attr_callback(SIREN_STATE_KEY, update_state)

    async def async_turn_on(self, **kwargs):
        """Turn the sirens on."""
        volume = int(kwargs.get("volume_level", 1.0) * 8)
        duration = kwargs.get("duration", 10)
        _LOGGER.debug("%s sirens on vol=%s, dur=%s", self.name, volume, duration)
        await asyncio.gather(*(
            siren.siren_on(duration=duration, volume=volume)
            for siren in self._sirens
        ))

        # Flip us on. update_state should confirm this.
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the sirens off."""
        _LOGGER.debug("%s sirens off", self.name)
        await asyncio.gather(*(
            siren.siren_off()
            for siren in self._sirens
        ))
        self._attr_is_on = False
        self.async_write_ha_state()


class AarloSiren(AarloSirenBase):
    """Representation of an Aarlo Siren."""

    def __init__(self, device):

        super().__init__(
            [device],
            "Siren",
            f"{COMPONENT_DOMAIN}_siren_{device.device_id}",
            device.device_id,
            suggested_object_id=f"aarlo_{slugify(device.name if isinstance(getattr(device, "name", None), str) else str(getattr(device, "device_id", "device")))}_siren",
            has_entity_name=True,
        )

        _LOGGER.info(f"ArloSiren: {self.name} created")


class AarloAllSirens(AarloSirenBase):
    """Representation of an Aarlo Siren."""

    def __init__(self, arlo, devices):

        super().__init__(
            devices,
            "All Arlo Sirens",
            f"{COMPONENT_DOMAIN}_all_sirens",
            arlo.device_id,
            suggested_object_id="aarlo_all_sirens",
            has_entity_name=False,
        )

        _LOGGER.info(f"ArloAllSirens: {self._attr_name} created")
