"""
Support for Arlo Cameras.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
https://www.home-assistant.io/integrations/camera
"""
from __future__ import annotations

import asyncio
import base64
import logging
import voluptuous as vol
from collections.abc import Callable
from haffmpeg.camera import CameraMjpeg

import homeassistant.helpers.config_validation as cv
from homeassistant.components import websocket_api
from homeassistant.components.camera.const import (
    CameraState
)
from homeassistant.components.camera import (
    ATTR_FILENAME,
    CONF_DURATION,
    CONF_LOOKBACK,
    Camera,
    CameraEntityFeature,
    DOMAIN as CAMERA_DOMAIN,
    SERVICE_RECORD,
    WebRTCAnswer,
    WebRTCClientConfiguration,
    WebRTCSendMessage,
)
from homeassistant.components.ffmpeg import DATA_FFMPEG
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_BATTERY_LEVEL,
    ATTR_ENTITY_ID,
    CONF_FILENAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_aiohttp_proxy_stream
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from webrtc_models import RTCIceServer

import pyaarlo
from pyaarlo.sip import ArloSipError
from pyaarlo.constant import (
    ACTIVITY_STATE_KEY,
    CHARGER_KEY,
    CHARGING_KEY,
    CONNECTION_KEY,
    LAST_IMAGE_DATA_KEY,
    LAST_IMAGE_KEY,
    LAST_IMAGE_SRC_KEY,
    MEDIA_UPLOAD_KEY,
    PRIVACY_KEY,
    RECENT_ACTIVITY_KEY,
    SIREN_STATE_KEY,
)

from .const import (
    ATTR_BATTERY_TECH,
    ATTR_CHARGER_TYPE,
    COMPONENT_ATTRIBUTION,
    COMPONENT_BRAND,
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
    COMPONENT_SERVICES,
    CONF_ADD_AARLO_PREFIX,
    CONF_SAVE_UPDATES_TO,
    CONF_STREAM_SNAPSHOT,
    STATE_ALARM_ARLO_ARMED,
    STATE_ALARM_ARLO_DISARMED,
)
from .utils import get_entity_from_domain


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [COMPONENT_DOMAIN, "ffmpeg"]

ATTR_BRIGHTNESS = "brightness"
ATTR_FLIPPED = "flipped"
ATTR_MIRRORED = "mirrored"
ATTR_MOTION = "motion_detection_sensitivity"
ATTR_POWERSAVE = "power_save_mode"
ATTR_SIGNAL_STRENGTH = "signal_strength"
ATTR_UNSEEN_VIDEOS = "unseen_videos"
ATTR_RECENT_ACTIVITY = "recent_activity"
ATTR_IMAGE_SRC = "image_source"
ATTR_CHARGING = "charging"
ATTR_WIRED = "wired"
ATTR_WIRED_ONLY = "wired_only"
ATTR_LAST_VIDEO = "last_video"
ATTR_VOLUME = "volume"
ATTR_LAST_THUMBNAIL = "last_thumbnail"
ATTR_DURATION = "duration"
ATTR_TIME_ZONE = "time_zone"
ATTR_STATE = "state"

CONF_FFMPEG_ARGUMENTS = "ffmpeg_arguments"
DEFAULT_FFMPEG_ARGUMENTS = "-pred 1 -q:v 2 -r 5"

POWERSAVE_MODE_MAPPING = {1: "best_battery_life", 2: "optimized", 3: "best_video"}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_FFMPEG_ARGUMENTS): cv.string,
})

CAMERA_SERVICE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids})
CAMERA_SERVICE_SNAPSHOT = CAMERA_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_FILENAME): cv.template
})

ICE_GATHER_DEBOUNCE_SECONDS = 0.3
ICE_GATHER_MAX_WAIT_SECONDS = 2.0

SERVICE_REQUEST_SNAPSHOT = "camera_request_snapshot"
SERVICE_REQUEST_SNAPSHOT_TO_FILE = "camera_request_snapshot_to_file"
SERVICE_REQUEST_VIDEO_TO_FILE = "camera_request_video_to_file"
SERVICE_STOP_ACTIVITY = "camera_stop_activity"
SERVICE_RECORD_START = "camera_start_recording"
SERVICE_RECORD_STOP = "camera_stop_recording"
SIREN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_DURATION): cv.positive_int,
    vol.Required(ATTR_VOLUME): cv.positive_int,
})
SIREN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
})
RECORD_START_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_DURATION): cv.positive_int,
})

WS_TYPE_VIDEO_URL = "aarlo_video_url"
WS_TYPE_LIBRARY = "aarlo_library"
WS_TYPE_STREAM_URL = "aarlo_stream_url"
WS_TYPE_SNAPSHOT_IMAGE = "aarlo_snapshot_image"
WS_TYPE_REQUEST_SNAPSHOT = "aarlo_request_snapshot"
WS_TYPE_VIDEO_DATA = "aarlo_video_data"
WS_TYPE_STOP_ACTIVITY = "aarlo_stop_activity"
WS_TYPE_SIREN_ON = "aarlo_camera_siren_on"
WS_TYPE_SIREN_OFF = "aarlo_camera_siren_off"
SCHEMA_WS_VIDEO_URL = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_VIDEO_URL,
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("index"): cv.positive_int,
})
SCHEMA_WS_LIBRARY = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_LIBRARY,
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("at_most"): cv.positive_int,
})
SCHEMA_WS_STREAM_URL = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_STREAM_URL,
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("user_agent"): cv.string,
})
SCHEMA_WS_SNAPSHOT_IMAGE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_SNAPSHOT_IMAGE,
    vol.Required("entity_id"): cv.entity_id,
})
SCHEMA_WS_REQUEST_SNAPSHOT = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_REQUEST_SNAPSHOT,
    vol.Required("entity_id"): cv.entity_id,
})
SCHEMA_WS_VIDEO_DATA = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_VIDEO_DATA, vol.Required("entity_id"): cv.entity_id
})
SCHEMA_WS_STOP_ACTIVITY = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_STOP_ACTIVITY,
    vol.Required("entity_id"): cv.entity_id,
})
SCHEMA_WS_SIREN_ON = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_SIREN_ON,
    vol.Required("entity_id"): cv.entity_id,
    vol.Required(ATTR_DURATION): cv.positive_int,
    vol.Required(ATTR_VOLUME): cv.positive_int,
})
SCHEMA_WS_SIREN_OFF = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required("type"): WS_TYPE_SIREN_OFF, vol.Required("entity_id"): cv.entity_id
})


def _sip_capable_cameras(arlo) -> set[str]:
    """Return the device ids of the cameras that speak SIP/WebRTC.

    Runs in an executor: the first lookup per model hits Arlo's capability
    endpoint. A camera that can't be classified - no capability document,
    network hiccup - is simply left off the list and keeps the RTSPS path.
    """
    capable = set()
    for camera in arlo.cameras:
        try:
            if camera.supports_sip_streaming:
                _LOGGER.info(f"{camera.name} supports SIP/WebRTC streaming")
                capable.add(camera.device_id)
        except Exception as e:
            _LOGGER.warning(f"could not read SIP capability for {camera.name}: {e}")
    return capable


async def async_setup_entry(
        hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: Callable[[list], None],
) -> None:
    """Set up an Arlo IP Camera."""

    arlo = hass.data[COMPONENT_DATA]
    aarlo_config = hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN]

    sip_capable = await hass.async_add_executor_job(_sip_capable_cameras, arlo)

    cameras = []
    cameras_with_siren = False
    for camera in arlo.cameras:
        if camera.device_id in sip_capable:
            cameras.append(ArloSipCam(camera, aarlo_config, hass))
        else:
            cameras.append(ArloCam(camera, aarlo_config, hass))
        if camera.has_capability(SIREN_STATE_KEY):
            cameras_with_siren = True

    async_add_entities(cameras)

    # Component services
    def service_callback(call):
        """Call aarlo service handler."""
        _LOGGER.info("{} service called".format(call.service))
        if call.service == SERVICE_REQUEST_SNAPSHOT:
            camera_snapshot_service(hass, call)
        if call.service == SERVICE_REQUEST_SNAPSHOT_TO_FILE:
            camera_snapshot_to_file_service(hass, call)
        if call.service == SERVICE_REQUEST_VIDEO_TO_FILE:
            camera_video_to_file_service(hass, call)
        if call.service == SERVICE_STOP_ACTIVITY:
            camera_stop_activity_service(hass, call)
        if call.service == SERVICE_RECORD_START:
            camera_start_recording_service(hass, call)
        if call.service == SERVICE_RECORD_STOP:
            camera_stop_recording_service(hass, call)

    async def async_service_callback(call):
        await hass.async_add_executor_job(service_callback, call)

    if not hasattr(hass.data[COMPONENT_SERVICES], CAMERA_DOMAIN):
        _LOGGER.info("installing handlers")
        hass.data[COMPONENT_SERVICES][CAMERA_DOMAIN] = "installed"
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_REQUEST_SNAPSHOT,
            async_service_callback,
            schema=CAMERA_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_REQUEST_SNAPSHOT_TO_FILE,
            async_service_callback,
            schema=CAMERA_SERVICE_SNAPSHOT,
        )
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_REQUEST_VIDEO_TO_FILE,
            async_service_callback,
            schema=CAMERA_SERVICE_SNAPSHOT,
        )
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_STOP_ACTIVITY,
            async_service_callback,
            schema=CAMERA_SERVICE_SCHEMA,
        )
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_RECORD_START,
            async_service_callback,
            schema=RECORD_START_SCHEMA,
        )
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_RECORD_STOP,
            async_service_callback,
            schema=CAMERA_SERVICE_SCHEMA,
        )

    # Websockets
    websocket_api.async_register_command(
        hass, WS_TYPE_VIDEO_URL, websocket_video_url, SCHEMA_WS_VIDEO_URL
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_LIBRARY, websocket_library, SCHEMA_WS_LIBRARY
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_STREAM_URL, websocket_stream_url, SCHEMA_WS_STREAM_URL
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_SNAPSHOT_IMAGE, websocket_snapshot_image, SCHEMA_WS_SNAPSHOT_IMAGE
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_REQUEST_SNAPSHOT, websocket_request_snapshot, SCHEMA_WS_REQUEST_SNAPSHOT
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_VIDEO_DATA, websocket_video_data, SCHEMA_WS_VIDEO_DATA
    )
    websocket_api.async_register_command(
        hass, WS_TYPE_STOP_ACTIVITY, websocket_stop_activity, SCHEMA_WS_STOP_ACTIVITY
    )
    if cameras_with_siren:
        websocket_api.async_register_command(
            hass, WS_TYPE_SIREN_ON, websocket_siren_on, SCHEMA_WS_SIREN_ON
        )
        websocket_api.async_register_command(
            hass, WS_TYPE_SIREN_OFF, websocket_siren_off, SCHEMA_WS_SIREN_OFF
        )


class ArloCam(Camera):
    """An implementation of a Netgear Arlo IP camera."""

    _camera: pyaarlo.ArloCamera | None = None
    _state: str | None = None
    _recent: bool = False
    _last_image_source: str | None = None
    _ffmpeg_arguments: str = DEFAULT_FFMPEG_ARGUMENTS
    _stream_snapshot: bool = False
    _save_updates_to: str | None = None

    def __init__(self, camera, aarlo_config, hass):
        """Initialize an Arlo camera."""
        super().__init__()
        
        self._camera = camera
        self._state: None
        self._recent: False
        self._last_image_source = None
        self._stream_snapshot = aarlo_config.get(CONF_STREAM_SNAPSHOT)
        self._save_updates_to = aarlo_config.get(CONF_SAVE_UPDATES_TO)
        self._ffmpeg = hass.data[DATA_FFMPEG]

        self._attr_name = camera.name
        self._attr_unique_id = camera.entity_id
        if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True):
            self.entity_id = f"{CAMERA_DOMAIN}.{COMPONENT_DOMAIN}_{self._attr_unique_id}"
        _LOGGER.debug(f"camera-entity-id={self.entity_id}")

        self._attr_brand = COMPONENT_BRAND
        # removed for issue #1019
        # self._attr_frontend_stream_type = StreamType.HLS
        self._attr_is_on = camera.is_on
        self._attr_model = camera.model_id
        self._attr_should_poll = False
        self._attr_supported_features = CameraEntityFeature.ON_OFF | CameraEntityFeature.STREAM
        self._attr_device_info = DeviceInfo(
            identifiers={(COMPONENT_DOMAIN, self._camera.device_id)},
            manufacturer=COMPONENT_BRAND,
        )
        _LOGGER.info(f"ArloCam: {self._attr_name} created")

    async def async_added_to_hass(self):
        """Register callbacks."""

        def update_state(_device, attr, value):
            _LOGGER.debug(f"callback:{self._attr_name}:{attr}:{str(value)[:120]}")

            # set state
            if attr == ACTIVITY_STATE_KEY or attr == CONNECTION_KEY:
                if value == "thermalShutdownCold":
                    self._state = "Offline, Too Cold"
                    self.clear_stream()
                elif value == "userStreamActive":
                    self._state = CameraState.STREAMING
                    self._attr_is_streaming = True
                elif value == "alertStreamActive":
                    self._state = CameraState.RECORDING
                    self._attr_is_recording = True
                elif value == "unavailable":
                    self._state = "Unavailable"
                    self.clear_stream()
                elif value == "fullFrameSnapshot":
                    self._attr_is_recording = True
                elif value == "startUserStream":
                    pass
                else:
                    self._state = CameraState.IDLE
                    self._attr_is_streaming = False
                    self._attr_is_recording = False
                    self.clear_stream()

            if attr == RECENT_ACTIVITY_KEY:
                self._recent = value

            # Trigger snapshot/capture/image updated events
            if attr == LAST_IMAGE_SRC_KEY:
                if (
                    self._last_image_source is not None
                    and self._last_image_source != value
                ):
                    if value.startswith("snapshot/"):
                        _LOGGER.debug("{0} snapshot updated".format(self.entity_id))
                        self.hass.bus.fire(
                            "aarlo_snapshot_updated",
                            {"entity_id": self.entity_id, "device_id": self.device_id},
                        )
                    else:
                        _LOGGER.debug("{0} capture updated".format(self.entity_id))
                        self.hass.bus.fire(
                            "aarlo_capture_updated",
                            {"entity_id": self.entity_id, "device_id": self.device_id},
                        )
                    self.hass.bus.fire(
                        "aarlo_image_updated",
                        {"entity_id": self.entity_id, "device_id": self.device_id},
                    )
                self._last_image_source = value

            # Save image if asked to
            if attr == LAST_IMAGE_DATA_KEY and self._save_updates_to != "":
                filename = "{}/{}.jpg".format(self._save_updates_to, self._attr_unique_id)
                _LOGGER.debug("saving to {}".format(filename))
                if not self.hass.config.is_allowed_path(filename):
                    _LOGGER.error("Can't write %s, no access to path!", filename)
                else:
                    with open(filename, "wb") as img_file:
                        img_file.write(value)

            # Is the camera on or off?
            if attr == PRIVACY_KEY:
                self._attr_is_on = not value

            # Signal changes.
            self.schedule_update_ha_state()

        self._camera.add_attr_callback(ACTIVITY_STATE_KEY, update_state)
        self._camera.add_attr_callback(CHARGER_KEY, update_state)
        self._camera.add_attr_callback(CHARGING_KEY, update_state)
        self._camera.add_attr_callback(CONNECTION_KEY, update_state)
        self._camera.add_attr_callback(LAST_IMAGE_KEY, update_state)
        self._camera.add_attr_callback(LAST_IMAGE_SRC_KEY, update_state)
        self._camera.add_attr_callback(LAST_IMAGE_DATA_KEY, update_state)
        self._camera.add_attr_callback(MEDIA_UPLOAD_KEY, update_state)
        self._camera.add_attr_callback(PRIVACY_KEY, update_state)
        self._camera.add_attr_callback(RECENT_ACTIVITY_KEY, update_state)

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        video = await self.hass.async_add_executor_job(
            getattr, self._camera, "last_video"
        )

        if not video:
            error_msg = (
                f"Video not found for {self._attr_name}. "
                f"Is it older than {self._camera.min_days_vdo_cache} days?"
            )
            _LOGGER.error(error_msg)
            return

        stream = CameraMjpeg(self._ffmpeg.binary)
        await stream.open_camera(video.video_url, extra_cmd=self._ffmpeg_arguments)

        try:
            stream_reader = await stream.get_reader()
            return await async_aiohttp_proxy_stream(
                self.hass,
                request,
                stream_reader,
                self._ffmpeg.ffmpeg_stream_content_type,
            )
        finally:
            try:
                await stream.close()
            except Exception as e:
                _LOGGER.debug(f"problem with stream close for {self._attr_name} {str(e)}")

    def clear_stream(self):
        """Clear out inactive stream.

        Arlo stream changes frequently, so we trap that and clear down the stream device.
        """
        if hasattr(self, "stream"):
            if self.stream:
                _LOGGER.debug("clearing out stream variable")
                asyncio.run_coroutine_threadsafe(
                    self.stream.stop(), self.hass.loop
                )
                self.stream = None

    @property
    def device_id(self):
        """Return a unique ID."""
        return self._camera.device_id

    def turn_off(self) -> None:
        self._camera.turn_off()

    def turn_on(self) -> None:
        self._camera.turn_on()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            name: value
            for name, value in (
                (ATTR_BATTERY_LEVEL, self._camera.battery_level),
                (ATTR_BATTERY_TECH, self._camera.battery_tech),
                (ATTR_BRIGHTNESS, self._camera.brightness),
                (ATTR_FLIPPED, self._camera.flip_state),
                (ATTR_MIRRORED, self._camera.mirror_state),
                (ATTR_MOTION, self._camera.motion_detection_sensitivity),
                (
                    ATTR_POWERSAVE,
                    POWERSAVE_MODE_MAPPING.get(self._camera.powersave_mode),
                ),
                (ATTR_SIGNAL_STRENGTH, self._camera.signal_strength),
                (ATTR_UNSEEN_VIDEOS, self._camera.unseen_videos),
                (ATTR_RECENT_ACTIVITY, self._camera.was_recently_active),
                (ATTR_IMAGE_SRC, self._camera.last_image_source),
                (ATTR_CHARGING, self._camera.is_charging),
                (ATTR_CHARGER_TYPE, self._camera.charger_type),
                (ATTR_WIRED, self._camera.has_charger),
                (ATTR_WIRED_ONLY, self._camera.is_charger_only),
                (ATTR_LAST_THUMBNAIL, self.last_thumbnail_url),
                (ATTR_LAST_VIDEO, self.last_video_url),
                (ATTR_TIME_ZONE, self._camera.timezone),
                (ATTR_STATE, self._camera.state),
            )
            if value is not None
        }

        attrs.update({
            ATTR_ATTRIBUTION: COMPONENT_ATTRIBUTION,
            "name": self._attr_name,
            "has_siren": self._camera.has_capability(SIREN_STATE_KEY),
            "device_brand": COMPONENT_BRAND,
            "device_id": self._camera.device_id,
            "device_model": self._camera.model_id,
        })

        return attrs

    async def stream_source(self):
        """Return the source of the stream.

        Note, this is only used by `camera/stream` websocket, so we force the `User-Agent`
        to the original Arlo one. This means we get a `rtsps` stream back which the stream
        component can handle.
        """
        return await self.hass.async_add_executor_job(self._camera.get_stream, "arlo")

    async def async_stream_source(self, user_agent=None):
        return await self.hass.async_add_executor_job(
            self._camera.get_stream, user_agent
        )

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        return self._camera.last_image_from_cache

    @property
    def last_video(self):
        return self._camera.last_video

    @property
    def last_thumbnail_url(self):
        # prefer video or what arlo says?
        #  video = self._camera.last_video
        #  if video is None:
        #  thumbnail =  self._camera.last_image
        #  else:
        #  thumbnail = video.thumbnail_url
        #  return thumbnail
        return self._camera.last_image

    @property
    def last_video_url(self):
        video = self._camera.last_video
        return video.video_url if video is not None else None

    def last_n_videos(self, count):
        return self._camera.last_n_videos(count)

    @property
    def last_capture_date_format(self):
        return self._camera.last_capture_date_format

    def set_base_station_mode(self, mode):
        """Set the mode in the base station."""
        self._camera.base_station.mode = mode

    def enable_motion_detection(self):
        """Enable the Motion detection in base station (Arm)."""
        self._attr_motion_detection_enabled = True
        self.set_base_station_mode(STATE_ALARM_ARLO_ARMED)

    def disable_motion_detection(self):
        """Disable the motion detection in base station (Disarm)."""
        self._attr_motion_detection_enabled = False
        self.set_base_station_mode(STATE_ALARM_ARLO_DISARMED)

    def _attach_hidden_stream(self, duration):
        _LOGGER.info(f"{self._attr_unique_id} attaching hidden stream for duration {duration}")

        data = {
            "entity_id": self.entity_id,
            CONF_FILENAME: f"/tmp/aarlo-hidden-{self._attr_unique_id}.mp4",
            CONF_DURATION: duration,
            CONF_LOOKBACK: 0,
        }
        self.hass.services.call(CAMERA_DOMAIN, SERVICE_RECORD, data, blocking=False)

        _LOGGER.debug("waiting on stream connect")
        return self._camera.wait_for_user_stream()

    def _start_snapshot_stream(self):
        if self._stream_snapshot:
            source = self._camera.start_snapshot_stream()
            if source is not None:
                self._camera.wait_for_user_stream()
            return source
        return None

    def request_snapshot(self):
        self._start_snapshot_stream()
        self._camera.request_snapshot()

    async def async_request_snapshot(self):
        return await self.hass.async_add_executor_job(self.request_snapshot)

    def get_snapshot(self):
        self._start_snapshot_stream()
        return self._camera.get_snapshot()

    async def async_get_snapshot(self):
        return await self.hass.async_add_executor_job(self.get_snapshot)

    def get_video(self):
        return self._camera.get_video()

    async def async_get_video(self):
        return await self.hass.async_add_executor_job(self.get_video)

    def stop_activity(self):
        return self._camera.stop_activity()

    async def async_stop_activity(self):
        return await self.hass.async_add_executor_job(self.stop_activity)

    def siren_on(self, duration=30, volume=10):
        if self._camera.has_capability(SIREN_STATE_KEY):
            _LOGGER.debug(
                "{0} siren on {1}/{2}".format(self.unique_id, volume, duration)
            )
            self._camera.siren_on(duration=duration, volume=volume)
            return True
        return False

    def siren_off(self):
        if self._camera.has_capability(SIREN_STATE_KEY):
            _LOGGER.debug("{0} siren off".format(self.unique_id))
            self._camera.siren_off()
            return True
        return False

    async def async_siren_on(self, duration, volume):
        return await self.hass.async_add_executor_job(self.siren_on, duration, volume)

    async def async_siren_off(self):
        return await self.hass.async_add_executor_job(self.siren_off)

    def start_recording(self, duration=30):
        """ Create a recording in the Arlo library.

        Has to do 3 things:
        - start a stream on the camera
        - attach a dummy local stream to tell Arlo to really start the stream
        - send a "record-this-stream" request.

        We force the "arlo" user agent to get an rtsp stream.
        """
        source = self._camera.start_recording_stream(user_agent="arlo")
        if source:
            _LOGGER.debug(f"stream-url={source}")
            active = self._attach_hidden_stream(duration + 10)
            if active:
                _LOGGER.debug("attached, recording")
                self._camera.start_recording(duration=duration)
                return source
        _LOGGER.warning("failed to start recording for {}".format(self._camera.name))
        return None

    def stop_recording(self):
        self._camera.stop_recording_stream()

    async def async_start_recording(self, duration):
        return await self.hass.async_add_executor_job(self.start_recording, duration)

    async def async_stop_recording(self):
        return await self.hass.async_add_executor_job(self.stop_recording)


def _merge_trickled_candidates(
    offer_sdp: str, candidates: list[tuple[int, str]]
) -> str:
    """Splice trickled ICE candidates into their `m=` sections of an offer.

    `candidates` is `(sdp_m_line_index, candidate_line)` pairs, `candidate_line`
    already formatted as a bare `a=candidate:...` attribute line. Insertion
    happens from the last `m=` section backward so earlier insertions can't
    shift the line numbers of sections still to be processed.
    """
    if not candidates:
        return offer_sdp

    lines = offer_sdp.replace("\r\n", "\n").split("\n")
    m_line_positions = [i for i, line in enumerate(lines) if line.startswith("m=")]

    by_m_line: dict[int, list[str]] = {}
    for index, line in candidates:
        by_m_line.setdefault(index, []).append(line)

    for m_line_index in reversed(range(len(m_line_positions))):
        extra_lines = by_m_line.get(m_line_index)
        if not extra_lines:
            continue
        insert_at = m_line_positions[m_line_index] + 1
        lines[insert_at:insert_at] = extra_lines

    return "\r\n".join(line for line in lines if line != "") + "\r\n"


class ArloSipCam(ArloCam):
    """An Arlo camera that streams live video over SIP/WebRTC.

    This is the engine Arlo's own apps - including my.arlo.com in a browser -
    use for live view: SIP over a WebSocket carries the offer/answer exchange
    and the media flows peer-to-peer over WebRTC, with no `rtsps://` relay in
    the middle. pyaarlo handles only the signalling; the browser's own
    `RTCPeerConnection` is the other end, so Home Assistant never touches a
    media packet on this path.

    Why a subclass rather than a flag on `ArloCam`: Home Assistant decides
    whether a camera is a native WebRTC camera by comparing
    `type(self).async_handle_async_webrtc_offer` against `Camera`'s, once, in
    `Camera.__init__`. That check is class-level, so defining the override on
    `ArloCam` would claim WebRTC for *every* Arlo camera - including the ones
    that only speak RTSPS - and a native WebRTC camera advertises `WEB_RTC`
    *instead of* `HLS`. The `nest` integration splits its entities for exactly
    this reason.

    Everything else - snapshots, the library, the siren, recording, and the
    `aarlo_stream_url` websocket the Lovelace card uses - is inherited
    unchanged and still goes over RTSPS.
    """

    def __init__(self, camera, aarlo_config, hass):
        super().__init__(camera, aarlo_config, hass)
        self._ice_servers: list[RTCIceServer] = []
        self._sip_session_id: str | None = None
        self._pending_candidates: dict[str, tuple[list[tuple[int, str]], asyncio.Event]] = {}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.hass.async_create_background_task(
            self._async_refresh_ice_servers(),
            f"aarlo sip ice servers {self.entity_id}",
        )

    async def _async_refresh_ice_servers(self) -> None:
        """Re-read Arlo's published STUN/TURN servers.

        Cheap - one REST call, no signalling socket - so it runs at startup
        and again after each negotiation, keeping the TURN credentials we
        hand the browser reasonably fresh.
        """
        try:
            info = await self.hass.async_add_executor_job(self._camera.get_sip_info)
        except Exception as e:
            _LOGGER.debug(f"{self._attr_unique_id} could not refresh ICE servers: {e}")
            return
        self._ice_servers = [
            RTCIceServer(
                urls=server["urls"],
                username=server.get("username"),
                credential=server.get("credential"),
            )
            for server in info["ice_servers"]
        ]

    @callback
    def _async_get_webrtc_client_configuration(self) -> WebRTCClientConfiguration:
        """Hand the browser Arlo's own STUN/TURN servers.

        Home Assistant appends whatever ICE servers it is configured with on
        top of these, so a stale or empty list here degrades to those rather
        than breaking the stream.
        """
        config = WebRTCClientConfiguration()
        config.configuration.ice_servers.extend(self._ice_servers)
        return config

    def _negotiate_sip_stream(self, offer_sdp: str) -> str:
        """Trade the browser's offer for Arlo's answer. Blocking; executor only."""
        self._camera.stop_sip_stream()
        self._camera.get_sip_info()
        return self._camera.start_sip_stream(offer_sdp)

    async def _wait_for_ice_gathering(self, session_id: str) -> list[tuple[int, str]]:
        """Buffers trickled candidates until gathering looks finished.

        There's no explicit "gathering complete" signal from the frontend (see
        the module-level comment above `ICE_GATHER_DEBOUNCE_SECONDS`), so this
        resets a short debounce timer on every candidate and treats silence as
        done, bounded by a hard ceiling.
        """
        candidates: list[tuple[int, str]] = []
        new_candidate = asyncio.Event()
        self._pending_candidates[session_id] = (candidates, new_candidate)
        try:
            deadline = self.hass.loop.time() + ICE_GATHER_MAX_WAIT_SECONDS
            while True:
                new_candidate.clear()
                remaining = deadline - self.hass.loop.time()
                if remaining <= 0:
                    break
                try:
                    await asyncio.wait_for(
                        new_candidate.wait(), timeout=min(ICE_GATHER_DEBOUNCE_SECONDS, remaining)
                    )
                except asyncio.TimeoutError:
                    break
        finally:
            self._pending_candidates.pop(session_id, None)
        return candidates

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        """Negotiate a live stream for the browser's offer."""
        candidates = await self._wait_for_ice_gathering(session_id)
        full_offer_sdp = _merge_trickled_candidates(offer_sdp, candidates)
        try:
            answer_sdp = await self.hass.async_add_executor_job(
                self._negotiate_sip_stream, full_offer_sdp
            )
        except ArloSipError as e:
            raise HomeAssistantError(
                f"SIP negotiation failed for {self._attr_name}: {e}"
            ) from e

        self._sip_session_id = session_id
        _LOGGER.debug(f"{self._attr_unique_id} SIP session {session_id} established")
        send_message(WebRTCAnswer(answer_sdp))

        self.hass.async_create_background_task(
            self._async_refresh_ice_servers(),
            f"aarlo sip ice servers {self.entity_id}",
        )

    async def async_on_webrtc_candidate(self, session_id: str, candidate) -> None:
        """Buffers a trickled candidate for the offer still being assembled.

        Arlo's SIP proxy takes one complete offer in an INVITE and answers it
        once - there is no channel to trickle candidates into after the fact.
        So candidates arriving here are held and spliced into the offer SDP
        by `_wait_for_ice_gathering` / `_merge_trickled_candidates` before the
        INVITE ever goes out. Anything that arrives after that buffering
        window has closed is too late to matter and is dropped.

        `candidate` is deliberately unannotated: its type moved from
        `RTCIceCandidate` to `RTCIceCandidateInit` in 2024.12, and importing
        the newer name at module scope would break the whole camera platform
        - not just SIP - on the 2024.11 this integration still supports.
        """
        pending = self._pending_candidates.get(session_id)
        if pending is None:
            return
        candidates, new_candidate = pending
        if candidate.candidate:
            index = candidate.sdp_m_line_index or 0
            candidates.append((index, f"a={candidate.candidate}"))
        new_candidate.set()

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        """Hang up the SIP call behind a session the frontend has dropped."""
        if self._sip_session_id == session_id:
            self._sip_session_id = None
            _LOGGER.debug(f"{self._attr_unique_id} closing SIP session {session_id}")
            self.hass.async_create_task(
                self.hass.async_add_executor_job(self._camera.stop_sip_stream)
            )
        super().close_webrtc_session(session_id)

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        if self._sip_session_id is not None:
            self.close_webrtc_session(self._sip_session_id)


@websocket_api.async_response
async def websocket_video_url(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        video = camera.last_video
        url = video.video_url if video is not None else None
        url_type = video.content_type if video is not None else None
        thumbnail = video.thumbnail_url if video is not None else None
        connection.send_message(
            websocket_api.result_message(
                msg["id"],
                {
                    "url": url,
                    "url_type": url_type,
                    "thumbnail": thumbnail,
                    "thumbnail_type": "image/jpeg",
                },
            )
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"], "video_url_ws", "Unable to fetch url ({})".format(str(error))
            )
        )
        _LOGGER.warning("{} video url websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_library(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        videos = []
        _LOGGER.debug("library+" + str(msg["at_most"]))
        for v in camera.last_n_videos(msg["at_most"]):
            videos.append(
                {
                    "created_at": v.created_at,
                    "created_at_pretty": v.created_at_pretty(
                        camera.last_capture_date_format
                    ),
                    "duration": v.media_duration_seconds,
                    "url": v.video_url,
                    "url_type": v.content_type,
                    "thumbnail": v.thumbnail_url,
                    "thumbnail_type": "image/jpeg",
                    "object": v.object_type,
                    "object_region": v.object_region,
                    "trigger": v.object_type,
                    "trigger_region": v.object_region,
                }
            )
        connection.send_message(
            websocket_api.result_message(
                msg["id"],
                {
                    "videos": videos,
                },
            )
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "library_ws",
                "Unable to fetch library ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} library websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_stream_url(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("stream_url for " + str(camera.unique_id))

        user_agent = msg.get("user_agent", "linux")
        if user_agent != "linux":
            user_agent = "!" + user_agent

        # start stream and force user agent to linux, this will return a `mpeg dash`
        # stream we can use directly from the Lovelace card
        stream = await camera.async_stream_source(user_agent=user_agent)
        connection.send_message(
            websocket_api.result_message(msg["id"], {"url": stream})
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "stream_url_ws",
                "Unable to fetch stream ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} stream url websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_snapshot_image(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("snapshot_image for " + str(camera.unique_id))

        image = await camera.async_get_snapshot()
        connection.send_message(
            websocket_api.result_message(
                msg["id"],
                {
                    "content_type": camera.content_type,
                    "content": base64.b64encode(image).decode("utf-8"),
                },
            )
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "snapshot_image_ws",
                "Unable to take snapshot ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} snapshot image websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_request_snapshot(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("request_snapshot_image for " + str(camera.unique_id))

        await camera.async_request_snapshot()
        connection.send_message(
            websocket_api.result_message(msg["id"], {"snapshot requested"})
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "requst_snapshot_ws",
                "Unable to request snapshot ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} snapshot request websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_video_data(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("video_data for " + str(camera.unique_id))

        video = await camera.async_get_video()
        connection.send_message(
            websocket_api.result_message(
                msg["id"],
                {
                    "content_type": "video/mp4",
                    "content": base64.b64encode(video).decode("utf-8"),
                },
            )
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "video_data_ws",
                "Unable to get video data ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} video data websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_stop_activity(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("stop_activity for " + str(camera.unique_id))

        stopped = await camera.async_stop_activity()
        connection.send_message(
            websocket_api.result_message(msg["id"], {"stopped": stopped})
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "stop_activity_ws",
                "Unable to stop activity ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} stop activity websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_siren_on(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("stop_activity for " + str(camera.unique_id))

        await camera.async_siren_on(duration=msg["duration"], volume=msg["volume"])
        connection.send_message(
            websocket_api.result_message(msg["id"], {"siren": "on"})
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "siren_on_ws",
                "Unable to turn siren on ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} siren on websocket failed".format(msg["entity_id"]))


@websocket_api.async_response
async def websocket_siren_off(hass, connection, msg):
    try:
        camera = get_entity_from_domain(hass, CAMERA_DOMAIN, msg["entity_id"])
        _LOGGER.debug("stop_activity for " + str(camera.unique_id))

        await camera.async_siren_off()
        connection.send_message(
            websocket_api.result_message(msg["id"], {"siren": "off"})
        )
    except HomeAssistantError as error:
        connection.send_message(
            websocket_api.error_message(
                msg["id"],
                "siren_off_ws",
                "Unable to turn siren off ({})".format(str(error)),
            )
        )
        _LOGGER.warning("{} siren off websocket failed".format(msg["entity_id"]))


def camera_snapshot_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            _LOGGER.info("{} snapshot".format(entity_id))
            camera = get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id)
            camera.get_snapshot()
            hass.bus.fire(
                "aarlo_snapshot_ready",
                {
                    "entity_id": entity_id,
                    "device_id": camera.device_id,
                },
            )
        except HomeAssistantError:
            _LOGGER.warning("{} snapshot service failed".format(entity_id))


def camera_snapshot_to_file_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            camera = get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id)
            filename = call.data[ATTR_FILENAME]
            filename.hass = hass
            snapshot_file = filename.async_render(variables={ATTR_ENTITY_ID: camera})
            _LOGGER.info("{} snapshot(filename={})".format(entity_id, filename))

            # check if we allow to access to that file
            if not hass.config.is_allowed_path(snapshot_file):
                _LOGGER.error("Can't write %s, no access to path!", snapshot_file)
                return

            # Get and write snapshot
            snapshot = camera.get_snapshot()
            with open(snapshot_file, "wb") as out_file:
                out_file.write(snapshot)

            hass.bus.fire(
                "aarlo_snapshot_ready",
                {
                    "entity_id": entity_id,
                    "device_id": camera.device_id,
                    "file": snapshot_file,
                },
            )
        except OSError as err:
            _LOGGER.error("Can't write snapshot to file: %s", err)
        except HomeAssistantError:
            _LOGGER.warning("{} snapshot to file service failed".format(entity_id))


def camera_video_to_file_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            camera = get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id)
            filename = call.data[ATTR_FILENAME]
            filename.hass = hass
            video_file = filename.async_render(variables={ATTR_ENTITY_ID: camera})
            _LOGGER.info("{} video to file {}".format(entity_id, filename))

            # check if we allow to access to that file
            if not hass.config.is_allowed_path(video_file):
                _LOGGER.error("Can't write %s, no access to path!", video_file)
                return

            # Get and write video
            video = camera.get_video()
            with open(video_file, "wb") as out_file:
                out_file.write(video)

            hass.bus.fire(
                "aarlo_video_ready", {"entity_id": entity_id, "file": video_file}
            )
        except OSError as err:
            _LOGGER.error("Can't write image to file: %s", err)
        except HomeAssistantError:
            _LOGGER.warning("{} video to file service failed".format(entity_id))
        _LOGGER.debug("{0} video to file finished".format(entity_id))


def camera_stop_activity_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            _LOGGER.info("{} stop activity".format(entity_id))
            get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id).stop_activity()
        except HomeAssistantError:
            _LOGGER.warning("{} stop activity service failed".format(entity_id))


def camera_start_recording_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            duration = call.data[ATTR_DURATION]
            _LOGGER.info("{} start recording(duration={})".format(entity_id, duration))
            camera = get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id)
            camera.start_recording(duration=duration)
        except HomeAssistantError as e:
            _LOGGER.warning(f"{entity_id} start recording service failed - {str(e)}")


def camera_stop_recording_service(hass, call):
    for entity_id in call.data["entity_id"]:
        try:
            _LOGGER.info("{} stop recording".format(entity_id))
            get_entity_from_domain(hass, CAMERA_DOMAIN, entity_id).stop_recording()
        except HomeAssistantError as e:
            _LOGGER.warning(f"{entity_id} stop recording service failed - {str(e)}")
