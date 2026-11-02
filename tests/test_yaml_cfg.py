import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "aarlo"))

from unittest.mock import AsyncMock, MagicMock
from custom_components.aarlo.cfg import _async_load_yaml, _async_save_yaml, _read_file, _write_file


@pytest.mark.asyncio
async def test_async_save_and_load_yaml_without_hass(tmp_path):
    yaml_path = str(tmp_path / "test_aarlo.yaml")
    data = {
        "aarlo": {
            "username": "user@example.com",
            "recent_time": 120,
            "save_media_to": "/media/arlo",
        }
    }

    # Save without hass (uses asyncio.to_thread)
    await _async_save_yaml(yaml_path, data)
    assert os.path.exists(yaml_path)

    # Load without hass
    loaded = await _async_load_yaml(yaml_path)
    assert loaded == data


@pytest.mark.asyncio
async def test_async_save_and_load_yaml_with_mock_hass(tmp_path):
    yaml_path = str(tmp_path / "test_aarlo_hass.yaml")
    data = {
        "aarlo": {
            "username": "user2@example.com",
            "backend": "mqtt",
        }
    }

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *args: fn(*args))

    # Save with hass (uses async_add_executor_job)
    await _async_save_yaml(mock_hass, yaml_path, data)
    assert os.path.exists(yaml_path)
    assert mock_hass.async_add_executor_job.called

    # Load with hass
    mock_hass.async_add_executor_job.reset_mock()
    loaded = await _async_load_yaml(mock_hass, yaml_path)
    assert loaded == data
    assert mock_hass.async_add_executor_job.called


@pytest.mark.asyncio
async def test_async_load_yaml_missing_file_returns_empty(tmp_path):
    missing_path = str(tmp_path / "nonexistent.yaml")
    loaded = await _async_load_yaml(missing_path)
    assert loaded == {}


@pytest.mark.asyncio
async def test_async_load_yaml_empty_file(tmp_path):
    empty_file = str(tmp_path / "empty.yaml")
    with open(empty_file, "w") as f:
        f.write("")
    loaded = await _async_load_yaml(empty_file)
    # parse_yaml on empty string returns None
    assert loaded is None or loaded == {}


@pytest.mark.asyncio
async def test_async_load_yaml_comment_only_file(tmp_path):
    comment_file = str(tmp_path / "comment.yaml")
    with open(comment_file, "w") as f:
        f.write("# only comments\n# no yaml content\n")
    loaded = await _async_load_yaml(comment_file)
    assert loaded is None or loaded == {}
