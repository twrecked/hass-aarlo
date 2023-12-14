"""
Support for Arlo Switches.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/switch/
"""

import logging
from collections.abc import Callable
from typing import Any
from datetime import datetime

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import callback, HassJob
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from pyaarlo.constant import (
    ACTIVITY_STATE_KEY,
    SILENT_MODE_KEY,
    SIREN_STATE_KEY
)

from .const import *
from .utils import to_bool


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN]

DEFAULT_TOGGLE_FOR = timedelta(seconds=1)
DEFAULT_TOGGLE_UNTIL_STR = "1970-01-01T00:00:00+00:00"
DEFAULT_TOGGLE_UNTIL = datetime.fromisoformat(DEFAULT_TOGGLE_UNTIL_STR)

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
        hass: HomeAssistantType,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None]
) -> None:

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]
    config = hass.data[COMPONENT_CONFIG][SWITCH_DOMAIN]
    _LOGGER.debug(f"switch={config}")

    devices = []
    adevices = []

    # See what cameras and bases have sirens.
    for base in arlo.base_stations:
        if base.has_capability(SIREN_STATE_KEY):
            adevices.append(base)
    for camera in arlo.cameras:
        if camera.has_capability(SIREN_STATE_KEY):
            adevices.append(camera)
    for doorbell in arlo.doorbells:
        if doorbell.has_capability(SIREN_STATE_KEY):
            adevices.append(doorbell)

    # Create individual switches if asked for
    if config.get(CONF_SIRENS) is True:
        for adevice in adevices:
            devices.append(AarloSirenSwitch(aarlo_config, config, adevice))

    # Then create all_sirens if asked for.
    if config.get(CONF_ALL_SIRENS) is True:
        if len(adevices) != 0:
            devices.append(AarloAllSirensSwitch(aarlo_config, config, arlo, adevices))

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

    def __init__(self, device, aarlo_config, name, identifier, icon):
        """Initialize the Aarlo switch device."""
        
        self._device = device

        self._attr_name = name
        self._attr_unique_id = slugify(identifier)
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{SWITCH_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"
        _LOGGER.debug(f"switch-entity-id={self.entity_id}")

        self._attr_icon = f"mdi:{icon}"
        self._attr_is_on = False
        self._attr_should_poll = False
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )

        _LOGGER.info(f"AarloSwitch: {self._attr_name} created")

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("implement turn on")

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("implement turn off")

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        return {
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "device_brand": COMPONENT_BRAND,
            "device_name": self._device.name,
            "device_id": self._device.device_id,
            "device_model": self._device.model_id,
        }


class AarloSirenBaseSwitch(AarloSwitch):
    """Representation of an Aarlo Momentary switch."""

    _allow_off: bool = False
    _on_for: timedelta = DEFAULT_TOGGLE_FOR
    _on_until: datetime | None = None
    _timer: Callable[[], None] | None = None

    def __init__(self, device, aarlo_config, name, identifier, icon, on_for, allow_off):
        """Initialize the Aarlo Momentary switch device."""
        super().__init__(device, aarlo_config, name, identifier, icon)

        self._on_for = on_for
        self._allow_off = allow_off

        _LOGGER.debug(f"on={on_for}, allow={allow_off}")

    async def _async_stop_activity(self, *_args: Any) -> None:
        if self._on_until is not None:
            self.do_off()
            self._on_until = None

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        if self._on_until is None:
            self.do_on()
            self._on_until = dt_util.utcnow() + self._on_for
            self._timer = async_track_point_in_time(
                self.hass, HassJob(self._async_stop_activity), self._on_until
            )
            _LOGGER.debug("turned on")

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        if self._allow_off:
            self.do_off()
            self._on_until = None
            _LOGGER.debug("forced off")

    def do_on(self):
        _LOGGER.debug("implement do on")

    def do_off(self):
        _LOGGER.debug("implement do off")


class AarloSirenSwitch(AarloSirenBaseSwitch):
    """Representation of an Aarlo switch."""

    _volume: int = 0

    def __init__(self, aarlo_config, config, device):
        """Initialize the Aarlo siren switch device."""
        super().__init__(
            device, aarlo_config,
            f"{device.name} Siren",
            f"siren_{device.entity_id}",
            "alarm-bell",
            config.get(CONF_SIREN_DURATION),
            config.get(CONF_SIREN_ALLOW_OFF),
        )

        self._volume = config.get(CONF_SIREN_VOLUME)

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug(f"siren-callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            self._attr_is_on = to_bool(value)
            self.async_schedule_update_ha_state()

        _LOGGER.debug(f"register siren callbacks for {self._device.name}")
        self._device.add_attr_callback(SIREN_STATE_KEY, update_state)

    def do_on(self):
        _LOGGER.debug(f"turned siren {self._attr_name} on")
        self._device.siren_on(
            duration=self._on_for.total_seconds(), volume=self._volume
        )

    def do_off(self):
        _LOGGER.debug(f"turned siren {self._attr_name} off")
        self._device.siren_off()


class AarloAllSirensSwitch(AarloSirenBaseSwitch):
    """Representation of an Aarlo switch."""

    def __init__(self, aarlo_config, config, arlo, devices):
        """Initialize the Aarlo siren switch device."""
        super().__init__(
            arlo, aarlo_config,
            "All Sirens",
            "all_sirens",
            "alarm-light",
            config.get(CONF_SIREN_DURATION),
            config.get(CONF_SIREN_ALLOW_OFF),
        )

        self._volume = config.get(CONF_SIREN_VOLUME)
        self._devices = devices

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug(f"all-siren-callback:{self._attr_name}:{attr}:{str(value)[:80]}")

            is_on = False
            for device in self._devices:
                if device.siren_state == "on":
                    is_on = True
            self._attr_is_on = is_on
            self.async_schedule_update_ha_state()

        for device in self._devices:
            _LOGGER.debug(f"register all siren callbacks for {device.name}")
            device.add_attr_callback(SIREN_STATE_KEY, update_state)

    def do_on(self):
        for device in self._devices:
            _LOGGER.debug(f"turned sirens on {device.name}")
            device.siren_on(duration=self._on_for.total_seconds(), volume=self._volume)

    def do_off(self):
        for device in self._devices:
            _LOGGER.debug(f"turned sirens off {device.name}")
            device.siren_off()


class AarloSnapshotSwitch(AarloSwitch):
    """Representation of an Aarlo switch."""

    def __init__(self, aarlo_config, config, camera):
        """Initialize the Aarlo snapshot switch device."""
        super().__init__(
            camera, aarlo_config,
            f"{camera.name} Snapshot",
            f"snapshot_{camera.entity_id}",
            "camera",
        )

        self._timeout = config.get(CONF_SNAPSHOT_TIMEOUT)

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug(f"snapshot-callback:{self._attr_name}:{attr}:{str(value)[:80]}")
            # XXX beef this check up in pyaarlo; idle == not taking a snapshot
            # self._attr_is_on = self._device.is_taking_snapshot
            self._attr_is_on = "snapshot" in value.lower()
            self.async_schedule_update_ha_state()

        self._device.add_attr_callback(ACTIVITY_STATE_KEY, update_state)

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"starting snapshot for {self._attr_name}")
        if not self._device.is_taking_snapshot:
            self._device.request_snapshot()
            self._attr_is_on = True

    def turn_off(self, **kwargs):
        _LOGGER.debug(f"cancelling snapshot for {self._attr_name}")
        if self._device.is_taking_snapshot:
            self._device.stop_activity()
            self._attr_is_on = True


class AarloSilentModeBaseSwitch(AarloSwitch):
    """Representation of an Aarlo Doorbell Silence switch."""

    _block: str = "all"

    def __init__(self, aarlo_config, name, identifier, doorbell, block):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(doorbell, aarlo_config, name, identifier, "doorbell")

        self._block = block

    def turn_off(self, **kwargs):
        # XXX pyaarlo needs looking at to stop traditional chimes
        _LOGGER.debug(f"Turning off silent mode for {self._attr_name}")
        self._device.silence_off()

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)[:100]}")
            if self._block == "calls":
                self._attr_is_on = self._device.calls_are_silenced
            elif self._block == "chimes":
                self._attr_is_on = self._device.chimes_are_silenced
            else:
                self._attr_is_on = self._device.is_silenced
            self.async_schedule_update_ha_state()

        self._device.add_attr_callback(SILENT_MODE_KEY, update_state)


class AarloSilentModeSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence chimes and calls.

    This switch will mute everything!
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            f"{doorbell.name} Silent Mode Chime Call",
            f"{doorbell.entity_id} Silent Mode Chime Call",
            doorbell,
            block="all",
        )

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent mode for {self._attr_name}")
        self._device.silence_on()


class AarloSilentModeChimeSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence chimes.

    This switch will mute just chimes.
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            f"{doorbell.name} Silent Mode Chime",
            f"{doorbell.entity_id} Silent Mode Chime",
            doorbell,
            block="chimes",
        )

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent chimes mode for {self._attr_name}")
        self._device.silence_chimes()


class AarloSilentModeCallSwitch(AarloSilentModeBaseSwitch):
    """Representation of an Aarlo switch to silence calls.

    This switch will mute just calls.
    """

    def __init__(self, aarlo_config, doorbell):
        """Initialize the Aarlo silent mode switch device."""
        super().__init__(
            aarlo_config,
            f"{doorbell.name} Silent Mode Call",
            f"{doorbell.entity_id} Silent Mode Call",
            doorbell,
            block="calls",
        )

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"Turning on silent calls mode for {self._attr_name}")
        self._device.silence_calls()
