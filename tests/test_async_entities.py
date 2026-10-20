"""Async unit tests for modernized Aarlo entity platforms."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.alarm_control_panel.const import AlarmControlPanelState
from homeassistant.components.media_player.const import MediaPlayerState, MediaType

from custom_components.aarlo.alarm_control_panel import ArloBaseStation
from custom_components.aarlo.light import ArloLight, ArloNightLight, ArloSpotlight
from custom_components.aarlo.media_player import ArloMediaPlayer
from custom_components.aarlo.sensor import ArloSensor, SENSOR_TYPES
from custom_components.aarlo.siren import AarloSiren
from custom_components.aarlo.switch import AarloSnapshotSwitch, AarloSirenSwitch
from custom_components.aarlo import async_login


@pytest.fixture
def mock_device():
    device = MagicMock()
    device.name = "Front Door"
    device.entity_id = "front_door"
    device.device_id = "device_123"
    device.model_id = "VMC4040P"
    device.turn_on = AsyncMock(return_value=True)
    device.turn_off = AsyncMock(return_value=True)
    device.siren_on = AsyncMock(return_value=True)
    device.siren_off = AsyncMock(return_value=True)
    device.set_mode = AsyncMock(return_value=True)
    device.request_snapshot = AsyncMock(return_value=True)
    device.stop_activity = AsyncMock(return_value=True)
    device.play_track = AsyncMock(return_value=True)
    device.pause_track = AsyncMock(return_value=True)
    device.previous_track = AsyncMock(return_value=True)
    device.next_track = AsyncMock(return_value=True)
    device.set_volume = AsyncMock(return_value=True)
    device.set_shuffle = AsyncMock(return_value=True)
    device.attribute = MagicMock(return_value="50")
    device.has_capability = MagicMock(return_value=True)
    device.is_taking_snapshot = False
    device.siren_state = "off"
    device.add_attr_callback = MagicMock()
    return device


@pytest.mark.asyncio
async def test_light_async_turn_on_and_off(mock_device):
    light = ArloLight(mock_device, {})
    light.hass = MagicMock()
    light.async_write_ha_state = MagicMock()

    await light.async_turn_on(brightness=180)
    mock_device.turn_on.assert_awaited_once_with(brightness=180, rgb=None)
    assert light.is_on is True

    await light.async_turn_off()
    mock_device.turn_off.assert_awaited_once()
    assert light.is_on is False


@pytest.mark.asyncio
async def test_siren_async_turn_on_and_off(mock_device):
    siren = AarloSiren(mock_device)
    siren.hass = MagicMock()
    siren.async_write_ha_state = MagicMock()

    await siren.async_turn_on(duration=15, volume_level=0.5)
    mock_device.siren_on.assert_awaited_once_with(duration=15, volume=4)
    assert siren.is_on is True

    await siren.async_turn_off()
    mock_device.siren_off.assert_awaited_once()
    assert siren.is_on is False


@pytest.mark.asyncio
async def test_snapshot_switch_async_turn_on_and_off(mock_device):
    switch = AarloSnapshotSwitch({}, {}, mock_device)
    switch.hass = MagicMock()
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()
    mock_device.request_snapshot.assert_awaited_once()
    assert switch.is_on is True

    mock_device.is_taking_snapshot = True
    await switch.async_turn_off()
    mock_device.stop_activity.assert_awaited_once()
    assert switch.is_on is False


@pytest.mark.asyncio
async def test_media_player_async_operations(mock_device):
    player = ArloMediaPlayer(mock_device, {})
    player.hass = MagicMock()
    player.async_write_ha_state = MagicMock()

    await player.async_media_play()
    mock_device.play_track.assert_awaited_once()
    assert player.state == MediaPlayerState.PLAYING

    await player.async_media_pause()
    mock_device.pause_track.assert_awaited_once()
    assert player.state == MediaPlayerState.PAUSED

    await player.async_set_volume_level(0.75)
    mock_device.set_volume.assert_awaited_once_with(mute=False, volume=75)
    assert player.volume_level == 0.75

    await player.async_set_shuffle(True)
    mock_device.set_shuffle.assert_awaited_once_with(shuffle=True)
    assert player.shuffle is True


@pytest.mark.asyncio
async def test_alarm_control_panel_async_operations(mock_device):
    config = {
        "disarmed_mode_name": "disarmed",
        "home_mode_name": "home",
        "away_mode_name": "armed",
        "night_mode_name": "night",
        "alarm_volume": 8,
        "trigger_time": 60,
    }
    panel = ArloBaseStation(mock_device, {}, config)
    panel.hass = MagicMock()
    panel.async_write_ha_state = MagicMock()

    await panel.async_alarm_arm_home()
    mock_device.set_mode.assert_awaited_with("home")

    await panel.async_alarm_arm_away()
    mock_device.set_mode.assert_awaited_with("armed")

    await panel.async_alarm_disarm()
    mock_device.set_mode.assert_awaited_with("disarmed")


@pytest.mark.asyncio
async def test_sensor_entity_native_value(mock_device):
    sensor = ArloSensor(None, mock_device, {}, "battery_level", SENSOR_TYPES["battery_level"])
    sensor.hass = MagicMock()
    sensor.schedule_update_ha_state = MagicMock()

    await sensor.async_added_to_hass()
    assert sensor.native_value == "50"
    assert sensor.native_unit_of_measurement == "%"


@pytest.mark.asyncio
async def test_async_login_success():
    hass = SimpleNamespace(config=SimpleNamespace(config_dir="/tmp", path=lambda p: f"/tmp/{p}"))
    mock_client = MagicMock()
    mock_client.is_connected = True

    with patch("pyaarlo.PyArlo.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_client
        client = await async_login(hass, {"username": "test@example.com", "password": "pw"})
        assert client is mock_client
        mock_create.assert_awaited_once()
