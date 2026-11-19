"""Regression tests for the file-free Arlo recording stream consumer."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.ffmpeg import DATA_FFMPEG
from homeassistant.exceptions import HomeAssistantError

from custom_components.aarlo.camera import ArloCam


SOURCE = "rtsps://example.test/stream?token=signed-url"


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.exited = asyncio.Event()
        self.reaped = False

    async def wait(self):
        await self.exited.wait()
        self.reaped = True
        return self.returncode

    def exit(self, code):
        self.returncode = code
        self.exited.set()

    def kill(self):
        self.exit(-9)


@pytest.fixture
def camera():
    device = MagicMock()
    device.name = "Test camera"
    device.entity_id = "test_camera"
    device.start_recording_stream = AsyncMock(return_value=SOURCE)
    device.start_recording = AsyncMock(return_value=SOURCE)
    device.stop_recording_stream = AsyncMock()
    device.wait_for_user_stream = AsyncMock(return_value=True)
    hass = SimpleNamespace(
        data={DATA_FFMPEG: SimpleNamespace(binary="ffmpeg")},
        config=SimpleNamespace(time_zone="America/New_York"),
        async_create_background_task=lambda coro, name: asyncio.create_task(coro, name=name),
    )
    camera = ArloCam(device, {}, hass)
    camera.hass = hass
    return camera


@pytest.fixture
def ffmpeg(monkeypatch):
    process = FakeProcess()
    launch = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    return process, launch


@pytest.mark.asyncio
@pytest.mark.parametrize("stop_method", ["async_stop_recording", "async_will_remove_from_hass"])
async def test_keeps_file_free_consumer_until_stop(camera, ffmpeg, stop_method):
    process, launch = ffmpeg

    async def wait_for_stream():
        launch.assert_awaited_once()
        camera._camera.start_recording.assert_not_awaited()
        return True

    camera._camera.wait_for_user_stream.side_effect = wait_for_stream
    assert await camera.async_start_recording(duration=30) == SOURCE
    camera._camera.start_recording.assert_awaited_once_with(
        duration=30, fallback_timezone="America/New_York"
    )
    args = launch.await_args.args
    assert args[0] == "ffmpeg"
    assert args[args.index("-i") + 1] == SOURCE
    assert args[-3:] == ("-f", "null", "-")
    assert process.returncode is None

    await getattr(camera, stop_method)()
    assert process.returncode == -9 and process.reaped
    camera._camera.stop_recording_stream.assert_awaited_once()
    assert camera._recording_consumer_task is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["early_exit", "launch_error", "not_ready", "cloud_error"])
async def test_start_failure_releases_stream(camera, ffmpeg, caplog, failure):
    process, launch = ffmpeg
    if failure == "early_exit":
        process.exit(1)
    elif failure == "launch_error":
        launch.side_effect = OSError("FFmpeg missing")
    elif failure == "not_ready":
        camera._camera.wait_for_user_stream.return_value = False
    else:
        camera._camera.start_recording.return_value = None

    assert await asyncio.wait_for(camera.async_start_recording(), timeout=2) is None
    if failure != "cloud_error":
        camera._camera.start_recording.assert_not_awaited()
    camera._camera.stop_recording_stream.assert_awaited_once()
    assert camera._recording_consumer_task is None
    if failure != "launch_error":
        assert process.reaped
    assert SOURCE not in caplog.text


@pytest.mark.asyncio
async def test_kills_and_reaps_consumer_at_deadline(camera, ffmpeg):
    process, _ = ffmpeg
    await camera._async_consume_recording_stream(SOURCE, 0, asyncio.Event())
    assert process.returncode == -9 and process.reaped


@pytest.mark.asyncio
async def test_rejects_file_url(camera, ffmpeg):
    _, launch = ffmpeg
    with pytest.raises(HomeAssistantError, match="Unsupported Arlo recording stream URL"):
        await camera._async_consume_recording_stream("file:///not-a-stream", 10, asyncio.Event())
    launch.assert_not_awaited()


@pytest.mark.asyncio
async def test_clean_consumer_exit_after_start_is_not_an_error(camera, ffmpeg, caplog):
    process, _ = ffmpeg
    assert await camera.async_start_recording() == SOURCE
    task = camera._recording_consumer_task
    assert task is not None
    process.exit(0)
    await task
    assert camera._recording_consumer_task is None
    assert "Recording stream consumer failed" not in caplog.text
