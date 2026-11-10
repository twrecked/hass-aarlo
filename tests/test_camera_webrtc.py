"""Unit tests for Arlo WebRTC streaming and ArloSipCam."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.camera import (
    CameraEntityFeature,
    StreamType,
    WebRTCAnswer,
    WebRTCClientConfiguration,
)
from homeassistant.components.ffmpeg import DATA_FFMPEG
from homeassistant.exceptions import HomeAssistantError
from pyaarlo.sip import ArloSipError
from webrtc_models import RTCIceServer

from custom_components.aarlo.camera import (
    ArloCam,
    ArloSipCam,
    _merge_trickled_candidates,
    async_setup_entry,
)
from custom_components.aarlo.const import (
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_DOMAIN,
    COMPONENT_SERVICES,
)


def test_merge_trickled_candidates_empty():
    offer = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
    res = _merge_trickled_candidates(offer, [])
    assert res == offer


def test_merge_trickled_candidates_splicing():
    offer = (
        "v=0\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
        "c=IN IP4 0.0.0.0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
        "c=IN IP4 0.0.0.0\r\n"
    )
    candidates = [
        (0, "a=candidate:1 1 udp 2122260223 192.168.1.5 50000 typ host"),
        (1, "a=candidate:2 1 udp 2122260223 192.168.1.5 50001 typ host"),
    ]
    merged = _merge_trickled_candidates(offer, candidates)
    lines = merged.split("\r\n")

    audio_idx = lines.index("m=audio 9 UDP/TLS/RTP/SAVPF 111")
    assert lines[audio_idx + 1] == "a=candidate:1 1 udp 2122260223 192.168.1.5 50000 typ host"

    video_idx = lines.index("m=video 9 UDP/TLS/RTP/SAVPF 96")
    assert lines[video_idx + 1] == "a=candidate:2 1 udp 2122260223 192.168.1.5 50001 typ host"


@pytest.fixture
def sip_camera():
    device = MagicMock()
    device.name = "Front Door Bell"
    device.entity_id = "front_door_bell"
    device.device_id = "device-123"
    device.model_id = "AVD2001A"
    device.interface_version = "i007"
    device.supports_sip_streaming = True
    device.is_on = True
    device.is_unavailable = False
    device.get_sip_info = AsyncMock(
        return_value={
            "ice_servers": [
                {
                    "urls": ["stun:stun.arlo.com:19302"],
                    "username": None,
                    "credential": None,
                },
                {
                    "urls": ["turn:turn.arlo.com:443"],
                    "username": "user1",
                    "credential": "pass1",
                },
            ]
        }
    )
    device.start_sip_stream = AsyncMock(return_value="v=0\r\nm=video 9 ...\r\n")
    device.stop_sip_stream = AsyncMock()

    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.time = MagicMock(return_value=100.0)
    hass.data = {DATA_FFMPEG: MagicMock()}
    hass.async_create_background_task = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: asyncio.create_task(coro))

    cam = ArloSipCam(device, {}, hass)
    cam.hass = hass
    cam._attr_unique_id = "unique_doorbell"
    cam._attr_name = "Front Door Bell"
    return cam


def test_webrtc_stream_type_detection(sip_camera):
    # ArloSipCam advertises WEB_RTC in capabilities
    if hasattr(sip_camera, "camera_capabilities"):
        assert StreamType.WEB_RTC in sip_camera.camera_capabilities.frontend_stream_types
    else:
        assert getattr(sip_camera, "frontend_stream_type") == StreamType.WEB_RTC

    # Regular ArloCam advertises HLS
    regular_device = MagicMock()
    regular_device.supports_sip_streaming = False
    regular_cam = ArloCam(regular_device, {}, sip_camera.hass)
    if hasattr(regular_cam, "camera_capabilities"):
        assert StreamType.HLS in regular_cam.camera_capabilities.frontend_stream_types
    else:
        assert getattr(regular_cam, "frontend_stream_type") == StreamType.HLS


@pytest.mark.asyncio
async def test_refresh_and_get_webrtc_client_configuration(sip_camera):
    await sip_camera._async_refresh_ice_servers()
    sip_camera._camera.get_sip_info.assert_awaited_once()

    config = sip_camera._async_get_webrtc_client_configuration()
    assert isinstance(config, WebRTCClientConfiguration)
    ice_urls = [s.urls[0] for s in config.configuration.ice_servers]
    assert "stun:stun.arlo.com:19302" in ice_urls
    assert "turn:turn.arlo.com:443" in ice_urls


@pytest.mark.asyncio
async def test_async_handle_webrtc_offer(sip_camera):
    await sip_camera._async_refresh_ice_servers()

    offer_sdp = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
    session_id = "test-session-1"
    send_message = MagicMock()

    candidate = SimpleNamespace(
        candidate="1 1 udp 2122260223 192.168.1.5 50000 typ host",
        sdp_m_line_index=0,
    )
    async def add_candidate_delayed():
        await asyncio.sleep(0.01)
        await sip_camera.async_on_webrtc_candidate(session_id, candidate)

    asyncio.create_task(add_candidate_delayed())

    with patch("custom_components.aarlo.camera.ICE_GATHER_DEBOUNCE_SECONDS", 0.05), \
         patch("custom_components.aarlo.camera.ICE_GATHER_MAX_WAIT_SECONDS", 0.2):
        await sip_camera.async_handle_async_webrtc_offer(offer_sdp, session_id, send_message)

    sip_camera._camera.start_sip_stream.assert_awaited_once()
    called_offer = sip_camera._camera.start_sip_stream.call_args[0][0]
    assert "a=candidate:1 1 udp 2122260223 192.168.1.5 50000 typ host" in called_offer

    send_message.assert_called_once()
    answer_arg = send_message.call_args[0][0]
    assert isinstance(answer_arg, WebRTCAnswer)
    assert answer_arg.answer == "v=0\r\nm=video 9 ...\r\n"

    sip_camera.close_webrtc_session(session_id)
    await asyncio.sleep(0.01)
    assert sip_camera._camera.stop_sip_stream.await_count == 2


@pytest.mark.asyncio
async def test_async_handle_webrtc_offer_error(sip_camera):
    sip_camera._camera.start_sip_stream.side_effect = ArloSipError("negotiation failed")

    with patch("custom_components.aarlo.camera.ICE_GATHER_DEBOUNCE_SECONDS", 0.01), \
         patch("custom_components.aarlo.camera.ICE_GATHER_MAX_WAIT_SECONDS", 0.02):
        with pytest.raises(HomeAssistantError) as exc_info:
            await sip_camera.async_handle_async_webrtc_offer("v=0\r\n", "sess-err", MagicMock())
        assert "SIP negotiation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_setup_entry_creates_sip_cam_for_capable():
    cam1 = MagicMock()
    cam1.name = "Doorbell"
    cam1.supports_sip_streaming = True
    cam1.has_capability = MagicMock(return_value=False)
    cam1.async_update_capabilities = AsyncMock()

    cam2 = MagicMock()
    cam2.name = "Old Camera"
    cam2.supports_sip_streaming = False
    cam2.has_capability = MagicMock(return_value=False)
    cam2.async_update_capabilities = AsyncMock()

    arlo = MagicMock()
    arlo.cameras = [cam1, cam2]

    hass = MagicMock()
    hass.data = {
        COMPONENT_DATA: arlo,
        COMPONENT_CONFIG: {COMPONENT_DOMAIN: {}},
        COMPONENT_SERVICES: {},
        DATA_FFMPEG: MagicMock(),
    }

    added_entities = []
    def async_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, MagicMock(), async_add_entities)

    assert len(added_entities) == 2
    assert isinstance(added_entities[0], ArloSipCam)
    assert not isinstance(added_entities[1], ArloSipCam)
    assert isinstance(added_entities[1], ArloCam)


@pytest.mark.asyncio
async def test_setup_entry_disabled_by_config():
    cam1 = MagicMock()
    cam1.name = "Doorbell"
    cam1.supports_sip_streaming = True
    cam1.has_capability = MagicMock(return_value=False)
    cam1.async_update_capabilities = AsyncMock()

    arlo = MagicMock()
    arlo.cameras = [cam1]

    hass = MagicMock()
    hass.data = {
        COMPONENT_DATA: arlo,
        COMPONENT_CONFIG: {COMPONENT_DOMAIN: {"webrtc": False}},
        COMPONENT_SERVICES: {},
        DATA_FFMPEG: MagicMock(),
    }

    added_entities = []
    def async_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, MagicMock(), async_add_entities)

    assert len(added_entities) == 1
    # When webrtc is False, even SIP-capable cameras must be created as standard ArloCam
    assert not isinstance(added_entities[0], ArloSipCam)
    assert isinstance(added_entities[0], ArloCam)
