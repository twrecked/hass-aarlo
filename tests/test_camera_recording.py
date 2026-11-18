"""Regression tests for the hidden stream used for Arlo cloud recordings."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.ffmpeg import DATA_FFMPEG
from homeassistant.exceptions import HomeAssistantError

from custom_components.aarlo.camera import ArloCam


@pytest.fixture
def camera(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    device = MagicMock(name="Arlo device")
    device.name = "Test camera"
    device.entity_id = "test_camera"
    device.start_recording_stream = AsyncMock(return_value="rtsps://example.test/stream")
    device.start_recording = AsyncMock(return_value="rtsps://example.test/stream")
    device.stop_recording_stream = AsyncMock()
    device.wait_for_user_stream = AsyncMock(return_value=True)
    hass = SimpleNamespace(
        data={DATA_FFMPEG: MagicMock()},
        config=SimpleNamespace(
            media_dirs={"local": str(media)},
            is_allowed_path=MagicMock(return_value=True),
        ),
        services=SimpleNamespace(async_call=AsyncMock()),
        async_add_executor_job=asyncio.to_thread,
        async_create_background_task=lambda coro, name: asyncio.create_task(coro, name=name),
    )
    cam = ArloCam(device, {}, hass)
    cam.hass = hass
    return cam


@pytest.mark.asyncio
@pytest.mark.parametrize("media_key", ["local", "recordings"])
async def test_recording_uses_media_dir_and_cleans_up_after_recorder(camera, tmp_path, media_key):
    media_dir = tmp_path / ("media" if media_key == "local" else "custom_media")
    media_dir.mkdir(exist_ok=True)
    camera.hass.config.media_dirs = {media_key: str(media_dir)}
    if media_key == "local":
        camera.hass.config.media_dirs = {
            "recordings": str(tmp_path), "local": str(media_dir)
        }
    recording = asyncio.Event()
    finish = asyncio.Event()

    async def record(domain, service, data, *, blocking):
        assert (domain, service, blocking) == ("camera", "record", True)
        assert data["entity_id"] == camera.entity_id
        assert data["duration"] == 30
        path = Path(data["filename"])
        assert path.parent == media_dir / "aarlo-temp"
        assert path.suffix == ".mp4"
        path.write_bytes(b"recording")
        path.with_suffix(".mp4.tmp").write_bytes(b"partial recording")
        recording.set()
        await finish.wait()

    camera.hass.services.async_call.side_effect = record
    camera._camera.wait_for_user_stream.side_effect = recording.wait

    assert await camera.async_start_recording(duration=20)
    camera._camera.start_recording.assert_awaited_once_with(duration=20)
    camera.hass.config.is_allowed_path.assert_called_once_with(
        camera.hass.services.async_call.call_args.args[2]["filename"]
    )
    assert len(list((media_dir / "aarlo-temp").iterdir())) == 2

    task = camera._hidden_recording_task
    assert task is not None
    finish.set()
    await task
    assert not list((media_dir / "aarlo-temp").iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["unconfigured", "disallowed", "symlink"])
async def test_unusable_media_dir_is_rejected_before_cloud_stream(camera, tmp_path, invalid):
    if invalid == "unconfigured":
        camera.hass.config.media_dirs = {}
    elif invalid == "disallowed":
        camera.hass.config.is_allowed_path.return_value = False
    else:
        (tmp_path / "media" / "aarlo-temp").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(HomeAssistantError, match="writable Home Assistant media directory"):
        await camera.async_start_recording()
    camera._camera.start_recording_stream.assert_not_awaited()
    camera.hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_recorder_error_releases_cloud_stream_and_cleans_partial_file(camera, tmp_path, caplog):
    waiting = asyncio.Event()

    async def record(domain, service, data, *, blocking):
        await waiting.wait()
        Path(data["filename"]).with_suffix(".mp4.tmp").touch()
        raise HomeAssistantError("disk full")

    async def wait_for_stream():
        waiting.set()
        await asyncio.Future()

    camera.hass.services.async_call.side_effect = record
    camera._camera.wait_for_user_stream.side_effect = wait_for_stream
    assert await asyncio.wait_for(camera.async_start_recording(), timeout=5) is None
    camera._camera.start_recording.assert_not_awaited()
    camera._camera.stop_recording_stream.assert_awaited_once()
    assert not list((tmp_path / "media" / "aarlo-temp").iterdir())
    assert "disk full" in caplog.text
