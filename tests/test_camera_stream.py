"""Camera stream regressions with synthetic devices and no cloud access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.camera.const import CameraState
from homeassistant.components.ffmpeg import DATA_FFMPEG
from pyaarlo.constant import ACTIVITY_STATE_KEY, CONNECTION_KEY

from custom_components.aarlo.camera import ArloCam


@pytest.fixture
def camera():
    device = MagicMock()
    device.name = "Test camera"
    device.entity_id = "test_camera"
    device.device_id = "synthetic-device"
    device.model_id = "synthetic-model"
    device.is_on = True
    device.is_unavailable = False
    hass = SimpleNamespace(
        data={DATA_FFMPEG: MagicMock()},
        async_add_executor_job=AsyncMock(),
        loop=MagicMock(),
    )
    camera = ArloCam(device, {}, hass)
    camera.hass = hass
    camera.schedule_update_ha_state = MagicMock()
    camera.clear_stream = MagicMock()
    return camera


async def subscribe(camera):
    await camera.async_added_to_hass()
    return {args[0]: args[1] for args, _ in camera._camera.add_attr_callback.call_args_list}


@pytest.mark.asyncio
async def test_online_connection_update_preserves_active_stream(camera):
    callbacks = await subscribe(camera)
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "userStreamActive")
    stream = camera.stream = SimpleNamespace(available=True)
    callbacks[CONNECTION_KEY](camera._camera, CONNECTION_KEY, "available")
    assert camera.is_streaming
    assert camera.state == CameraState.STREAMING
    assert camera.stream is stream
    camera.clear_stream.assert_not_called()


@pytest.mark.asyncio
async def test_recording_to_streaming_resets_recording_flag(camera):
    callbacks = await subscribe(camera)
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "alertStreamActive")
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "userStreamActive")
    assert camera.is_streaming
    assert not camera.is_recording
    assert camera.state == CameraState.STREAMING


@pytest.mark.asyncio
async def test_streaming_to_recording_resets_streaming_flag(camera):
    callbacks = await subscribe(camera)
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "userStreamActive")
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "alertStreamActive")
    assert camera.is_recording
    assert not camera.is_streaming
    assert camera.state == CameraState.RECORDING


@pytest.mark.asyncio
@pytest.mark.parametrize("attr,value", [(ACTIVITY_STATE_KEY, "idle"),
                                       (CONNECTION_KEY, "unavailable"),
                                       (CONNECTION_KEY, "thermalShutdownCold")])
async def test_end_or_disconnect_still_clears_stream(camera, attr, value):
    callbacks = await subscribe(camera)
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "userStreamActive")
    callbacks[attr](camera._camera, attr, value)
    camera.clear_stream.assert_called_once()
    assert not camera.is_streaming
    assert not camera.is_recording


@pytest.mark.asyncio
async def test_pending_stream_start_preserves_existing_stream(camera):
    callbacks = await subscribe(camera)
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "userStreamActive")
    callbacks[ACTIVITY_STATE_KEY](camera._camera, ACTIVITY_STATE_KEY, "startUserStream")
    assert camera.is_streaming
    camera.clear_stream.assert_not_called()


def test_failed_decoder_is_not_hidden_as_available(camera):
    camera.stream = SimpleNamespace(available=False)
    assert not camera.available
