"""Explicit stop must discard HA's decoder before stopping its cloud source."""

import asyncio
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.ffmpeg import DATA_FFMPEG
from homeassistant.components.stream import Stream

from custom_components.aarlo.camera import ArloCam


@pytest.fixture
def camera():
    device = MagicMock()
    device.name = "Test"
    device.entity_id = "test"
    device.device_id = "synthetic-device"
    device.model_id = "synthetic-model"
    hass = SimpleNamespace(data={DATA_FFMPEG: MagicMock()},
                           async_add_executor_job=AsyncMock(return_value=True))
    camera = ArloCam(device, {}, hass)
    camera.hass = hass
    return camera


@pytest.mark.asyncio
async def test_explicit_stop_discards_decoder_before_cloud_stop(camera):
    order = []

    async def decoder_stop():
        order.append("decoder")

    async def cloud_stop(_func):
        assert camera.stream is None
        order.append("cloud")
        return True

    old = camera.stream = SimpleNamespace(
        stop=AsyncMock(side_effect=decoder_stop),
        dynamic_stream_settings=SimpleNamespace(preload_stream=False),
    )
    camera.hass.async_add_executor_job.side_effect = cloud_stop
    assert await camera.async_stop_activity() is True
    assert camera.stream is None
    old.stop.assert_awaited_once_with()
    assert order == ["decoder", "cloud"]


@pytest.mark.asyncio
async def test_stop_without_decoder_still_stops_cloud(camera):
    camera.stream = None
    assert await camera.async_stop_activity() is True
    camera.hass.async_add_executor_job.assert_awaited_once_with(camera.stop_activity)


@pytest.mark.asyncio
async def test_decoder_stop_failure_still_attempts_cloud_stop(camera):
    old = camera.stream = SimpleNamespace(
        stop=AsyncMock(side_effect=RuntimeError("test")),
        dynamic_stream_settings=SimpleNamespace(preload_stream=False),
    )
    with pytest.raises(RuntimeError, match="test"):
        await camera.async_stop_activity()
    assert camera.stream is old
    camera.hass.async_add_executor_job.assert_awaited_once_with(camera.stop_activity)


@pytest.mark.asyncio
async def test_reopen_waits_for_stop_and_gets_a_fresh_source(camera, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()

    async def decoder_stop():
        entered.set()
        await release.wait()

    old = camera.stream = SimpleNamespace(
        stop=AsyncMock(side_effect=decoder_stop),
        dynamic_stream_settings=SimpleNamespace(preload_stream=False),
    )
    new = SimpleNamespace(set_update_callback=MagicMock())
    camera.stream_source = AsyncMock(return_value="rtsps://example.invalid/fresh")
    monkeypatch.setattr("homeassistant.components.camera.create_stream", MagicMock(return_value=new))
    monkeypatch.setattr("homeassistant.components.camera.get_dynamic_camera_stream_settings", AsyncMock(return_value={}))
    stopping = asyncio.create_task(camera.async_stop_activity())
    reopening = None
    try:
        await asyncio.wait_for(entered.wait(), 0.5)
        reopening = asyncio.create_task(camera.async_create_stream())
        await asyncio.sleep(0)
        assert not reopening.done()
        release.set()
        assert await stopping is True
        assert await reopening is new
        assert camera.stream is not old
        camera.stream_source.assert_awaited_once_with()
    finally:
        release.set()
        await stopping
        if reopening is not None:
            await reopening


@pytest.mark.asyncio
async def test_explicit_stop_terminates_a_preloaded_worker(camera):
    # Exercise HA's actual stop implementation: it otherwise keeps preloaded
    # workers running even after the integration discards the stream reference.
    old = camera.stream = SimpleNamespace(
        dynamic_stream_settings=SimpleNamespace(preload_stream=True),
        _stop=AsyncMock(),
    )
    old.stop = MethodType(Stream.stop, old)
    assert await camera.async_stop_activity() is True
    old._stop.assert_awaited_once_with()
    assert camera.stream is None
