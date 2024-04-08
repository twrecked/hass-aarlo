"""
Support for Arlo Media Players.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/media_player/
"""

import logging
from collections.abc import Callable

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature
)
from homeassistant.components.media_player.const import (
    MediaPlayerState,
    MediaType,
    MEDIA_TYPE_MUSIC,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from pyaarlo.constant import MEDIA_PLAYER_KEY

from .const import (
    COMPONENT_ATTRIBUTION,
    COMPONENT_BRAND,
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
    CONF_ADD_AARLO_PREFIX,
)


_LOGGER = logging.getLogger(__name__)

SUPPORT_ARLO = MediaPlayerEntityFeature(
    MediaPlayerEntityFeature.PAUSE |
    MediaPlayerEntityFeature.PLAY_MEDIA |
    MediaPlayerEntityFeature.PLAY |
    MediaPlayerEntityFeature.PREVIOUS_TRACK |
    MediaPlayerEntityFeature.NEXT_TRACK |
    MediaPlayerEntityFeature.SHUFFLE_SET |
    MediaPlayerEntityFeature.VOLUME_MUTE |
    MediaPlayerEntityFeature.VOLUME_SET
)

""" Unsupported features:

    SUPPORT_CLEAR_PLAYLIST
    SUPPORT_SEEK
    SUPPORT_SELECT_SOUND_MODE
    SUPPORT_SELECT_SOURCE
    SUPPORT_STOP
    SUPPORT_TURN_OFF
    SUPPORT_TURN_ON
    SUPPORT_VOLUME_STEP
"""


async def async_setup_entry(
        hass: HomeAssistantType,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo media player."""

    arlo = hass.data.get(COMPONENT_DATA)
    if not arlo:
        return

    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]

    players = []
    for camera in arlo.cameras:
        if camera.has_capability(MEDIA_PLAYER_KEY):
            players.append(ArloMediaPlayer(camera, aarlo_config))

    async_add_entities(players)


class ArloMediaPlayer(MediaPlayerEntity):
    """Representation of an arlo media player."""

    def __init__(self, device, aarlo_config):
        """Initialize an Arlo media player."""

        self._device = device
        self._position = 0
        self._track_id = None
        self._playlist = []

        self._attr_name = device.name
        self._attr_unique_id = device.entity_id
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{MEDIA_PLAYER_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"
        _LOGGER.debug(f"media-player-entity-id={self.entity_id}")

        self._attr_device_class = MediaPlayerDeviceClass.SPEAKER
        self._attr_icon = "mdi:speaker"
        self._attr_media_content_type = MediaType.MUSIC
        self._attr_muted = None
        self._attr_should_poll = False
        self._attr_shuffle = None
        self._attr_state = None
        self._attr_supported_features = SUPPORT_ARLO
        self._attr_volume = None
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._device.device_id)},
            manufacturer=COMPONENT_BRAND,
        )
        _LOGGER.info(f"ArloMediaPlayer: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, props):
            _LOGGER.info(f"callback:{self._attr_name}:{attr}:{str(props)[:80]}")
            if attr == "status":
                status = props.get("status")
                if status == "playing":
                    self._attr_state = MediaPlayerState.PLAYING
                elif status == "paused":
                    self._attr_state = MediaPlayerState.PAUSED
                else:
                    _LOGGER.debug("Unknown status:" + status)
                    self._attr_state = MediaPlayerState.IDLE
                self._position = props.get("position", 0)
                self._track_id = props.get("trackId", None)
            elif attr == "speaker":
                vol = props.get("volume")
                if vol is not None:
                    self._attr_volume = vol / 100
                self._attr_muted = props.get("mute", self._attr_muted)
            elif attr == "config":
                config = props.get("config", {})
                self._attr_shuffle = config.get("shuffleActive", self._attr_shuffle)
            elif attr == "playlist":
                self._playlist = props

            self.schedule_update_ha_state()

        self._device.add_attr_callback("config", update_state)
        self._device.add_attr_callback("speaker", update_state)
        self._device.add_attr_callback("status", update_state)
        self._device.add_attr_callback("playlist", update_state)
        self._device.get_audio_playback_status()

    @property
    def media_title(self):
        """Title of current playing media."""
        if self._track_id is not None and self._playlist:
            for track in self._playlist:
                if track.get("id") == self._track_id:
                    return track.get("title")
        return None

    def set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        self._device.set_shuffle(shuffle=shuffle)
        self._attr_shuffle = shuffle

    def media_previous_track(self):
        """Send next track command."""
        self._device.previous_track()

    def media_next_track(self):
        """Send next track command."""
        self._device.next_track()

    def mute_volume(self, mute):
        """Mute the volume."""
        self._device.set_volume(mute=mute, volume=int(self._attr_volume * 100))
        self._attr_muted = mute

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._device.set_volume(mute=False, volume=int(volume * 100))
        self._attr_volume = volume

    def media_play(self):
        """Send play command."""
        self._device.play_track()
        self._attr_state = MediaPlayerState.PLAYING

    def media_pause(self):
        """Send pause command."""
        self._device.pause_track()
        self._attr_state = MediaPlayerState.PAUSED

    def play_media(self, media_type, media_id, **kwargs):
        """Play media from a URL or file."""
        if not media_type == MEDIA_TYPE_MUSIC:
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MEDIA_TYPE_MUSIC,
            )
            return
        self._device.play_track()
        self._attr_state = MediaPlayerState.PLAYING

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
