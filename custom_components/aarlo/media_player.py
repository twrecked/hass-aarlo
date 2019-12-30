"""Provide functionality to interact with vlc devices on the network."""
import logging

import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerDevice
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_NEXT_TRACK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.core import callback
from homeassistant.const import CONF_NAME, STATE_IDLE, STATE_PAUSED, STATE_PLAYING
import homeassistant.helpers.config_validation as cv
from . import CONF_ATTRIBUTION, DATA_ARLO, DEFAULT_BRAND

_LOGGER = logging.getLogger(__name__)

SUPPORT_ARLO = (
    SUPPORT_PAUSE
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PLAY
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_SET
    
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


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, _discovery_info=None):
    """Set up an Arlo media player."""
    arlo = hass.data.get(DATA_ARLO)
    if not arlo:
        return

    players = []
    for camera in arlo.cameras:
        if camera.has_capability('mediaPlayer'):
            name = 'Media Player {0}'.format(camera.name)
            players.append(ArloMediaPlayerDevice(name, camera))

    async_add_entities(players, True)

class ArloMediaPlayerDevice(MediaPlayerDevice):
    """Representation of an arlo media player."""

    def __init__(self, name, device):
        """Initialize an Arlo media player."""
        self._name = name
        self._unique_id = self._name.lower().replace(' ', '_')

        self._device = device
        self._name = name
        self._volume = None
        self._muted = None
        self._state = None
        self._position = 0
        _LOGGER.info('ArloMediaPlayerDevice: %s created', self._name)

    # def update(self):
    #     """Get the latest details from the device."""
    #     status = self._vlc.get_state()
    #     if status == vlc.State.Playing:
    #         self._state = STATE_PLAYING
    #     elif status == vlc.State.Paused:
    #         self._state = STATE_PAUSED
    #     else:
    #         self._state = STATE_IDLE
    #     self._media_duration = self._vlc.get_length() / 1000
    #     position = self._vlc.get_position() * self._media_duration
    #     if position != self._media_position:
    #         self._media_position_updated_at = dt_util.utcnow()
    #         self._media_position = position

    #     self._volume = self._vlc.audio_get_volume() / 100
    #     self._muted = self._vlc.audio_get_mute() == 1

    #     return True

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update_state(_device, attr, props):
            _LOGGER.debug('media_player callback:' + attr + ':' + str(props)[:80])
            if attr == "audioState":
                status = props.get('status')
                if status == 'playing':
                    self._state = STATE_PLAYING
                elif status == 'paused':
                    self._state = STATE_PAUSED
                else:
                    _LOGGER.debug('Unknown status:' + status)
                    self._state = STATE_IDLE
                self._position = props.get('position', 0)

            self.async_schedule_update_ha_state()

        self._device.add_attr_callback('audioState', update_state)
        self._device.add_attr_callback("status", update_state)
        self._device.add_attr_callback("position", update_state)
        self._device.add_attr_callback("trackId", update_state)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ARLO

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    def mute_volume(self, mute):
        """Mute the volume."""
        self._device.set_volume(mute=mute, volume=self._volume)
        self._muted = mute

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._device.set_volume(mute=False, volume=int(volume * 100))
        self._volume = volume

    def media_play(self):
        """Send play command."""
        self._device.play_track()
        self._state = STATE_PLAYING

    def media_pause(self):
        """Send pause command."""
        self._device.pause_track()
        self._state = STATE_PAUSED

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
        self._state = STATE_PLAYING
