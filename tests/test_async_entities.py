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
from custom_components.aarlo.switch import AarloSnapshotSwitch
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
    siren = AarloSiren(mock_device, {"device_first_naming": True})
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


@pytest.mark.asyncio
async def test_options_flow_general_step_first():
    from custom_components.aarlo.config_flow import ArloOptionsFlowHandler

    mock_entry = SimpleNamespace(
        options={"backend": "auto", "save_media_to": "/test/media"},
        entry_id="test_entry",
    )
    handler = ArloOptionsFlowHandler(mock_entry)
    handler.hass = SimpleNamespace(config=SimpleNamespace(path=lambda p: f"/tmp/{p}"))

    # Initial step should show 'general'
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "general"

    # Submitting general should proceed to 'alarm_control_panel'
    next_step = await handler.async_step_general({
        "backend": "mqtt",
        "http_backend": "curl_cffi",
        "save_media_to": "/config/media/test",
        "media_retention_days": 14,
    })
    assert next_step["type"] == "form"
    assert next_step["step_id"] == "alarm_control_panel"
    assert handler._config["backend"] == "mqtt"
    assert handler._config["save_media_to"] == "/config/media/test"
    assert handler._config["media_retention_days"] == 14


@pytest.mark.asyncio
async def test_entity_modern_naming_and_object_ids(mock_device):
    from custom_components.aarlo.camera import ArloCam
    from custom_components.aarlo.light import ArloFloodLight
    from custom_components.aarlo.binary_sensor import ArloBinarySensor, SENSOR_TYPES as BINARY_SENSOR_TYPES
    from custom_components.aarlo.siren import AarloAllSirens

    hass = MagicMock()
    hass.data = {"ffmpeg": MagicMock()}

    # Camera
    cam = ArloCam(mock_device, {}, hass)
    assert cam.has_entity_name is True
    assert cam._attr_name is None
    assert cam.suggested_object_id == "aarlo_front_door"
    assert cam.entity_id == "camera.aarlo_front_door"

    # Standalone Light
    light = ArloLight(mock_device, {})
    assert light.has_entity_name is True
    assert light._attr_name is None
    assert light.suggested_object_id == "aarlo_front_door"
    assert light.entity_id == "light.aarlo_front_door"

    # Camera Spotlight
    spotlight = ArloSpotlight(mock_device, {"device_first_naming": True})
    assert spotlight.has_entity_name is True
    assert spotlight._attr_name == "Spotlight"
    assert spotlight.suggested_object_id == "aarlo_front_door_spotlight"
    assert spotlight.entity_id == "light.aarlo_front_door_spotlight"

    # Camera Floodlight
    floodlight = ArloFloodLight(mock_device, {"device_first_naming": True})
    assert floodlight.has_entity_name is True
    assert floodlight._attr_name == "Floodlight"
    assert floodlight.suggested_object_id == "aarlo_front_door_floodlight"
    assert floodlight.entity_id == "light.aarlo_front_door_floodlight"

    # Siren
    siren = AarloSiren(mock_device, {"device_first_naming": True})
    assert siren.has_entity_name is True
    assert siren._attr_name == "Siren"
    assert siren.suggested_object_id == "aarlo_front_door_siren"
    assert siren.entity_id == "siren.aarlo_front_door_siren"

    # All Sirens Virtual Entity
    all_sirens = AarloAllSirens(MagicMock(), [mock_device])
    assert all_sirens.has_entity_name is False
    assert all_sirens._attr_name == "All Arlo Sirens"
    assert all_sirens.suggested_object_id == "aarlo_all_sirens"
    assert all_sirens.entity_id == "siren.aarlo_all_sirens"

    # Sensor - Modern (device_first_naming=True)
    sensor = ArloSensor(None, mock_device, {"device_first_naming": True}, "battery_level", SENSOR_TYPES["battery_level"])
    assert sensor.has_entity_name is True
    assert sensor._attr_name == "Battery Level"
    assert sensor.suggested_object_id == "aarlo_front_door_battery_level"
    assert sensor.entity_id == "sensor.aarlo_front_door_battery_level"
    assert sensor.unique_id == "front_door_battery_level"

    # Sensor - Legacy (device_first_naming=False, default for upgrades)
    sensor_legacy = ArloSensor(None, mock_device, {"device_first_naming": False}, "battery_level", SENSOR_TYPES["battery_level"])
    assert sensor_legacy.suggested_object_id == "aarlo_battery_level_front_door"
    assert sensor_legacy.entity_id == "sensor.aarlo_battery_level_front_door"
    assert sensor_legacy.unique_id == "battery_level_front_door"

    # Binary Sensor - Modern
    binary_sensor = ArloBinarySensor(mock_device, {"device_first_naming": True}, "motion", BINARY_SENSOR_TYPES["motion"])
    assert binary_sensor.has_entity_name is True
    assert binary_sensor._attr_name == "Motion"
    assert binary_sensor.suggested_object_id == "aarlo_front_door_motion"
    assert binary_sensor.entity_id == "binary_sensor.aarlo_front_door_motion"
    assert binary_sensor.unique_id == "front_door_motion"

    # Binary Sensor - Legacy
    binary_sensor_legacy = ArloBinarySensor(mock_device, {"device_first_naming": False}, "motion", BINARY_SENSOR_TYPES["motion"])
    assert binary_sensor_legacy.suggested_object_id == "aarlo_motion_front_door"
    assert binary_sensor_legacy.entity_id == "binary_sensor.aarlo_motion_front_door"
    assert binary_sensor_legacy.unique_id == "motion_front_door"

    # Snapshot Switch - Modern
    snap_switch = AarloSnapshotSwitch({"device_first_naming": True}, {}, mock_device)
    assert snap_switch.has_entity_name is True
    assert snap_switch._attr_name == "Snapshot"
    assert snap_switch.suggested_object_id == "aarlo_front_door_snapshot"
    assert snap_switch.entity_id == "switch.aarlo_front_door_snapshot"
    assert snap_switch.unique_id == "front_door_snapshot"

    # Snapshot Switch - Legacy
    snap_switch_legacy = AarloSnapshotSwitch({"device_first_naming": False}, {}, mock_device)
    assert snap_switch_legacy.suggested_object_id == "aarlo_snapshot_front_door"
    assert snap_switch_legacy.entity_id == "switch.aarlo_snapshot_front_door"
    assert snap_switch_legacy.unique_id == "snapshot_front_door"




@pytest.mark.asyncio
async def test_light_async_setup_entry_maps_pyaarlo_lights():
    from custom_components.aarlo.light import async_setup_entry, ArloSpotlight, ArloFloodLight, ArloLight, ArloNightLight
    from custom_components.aarlo.const import COMPONENT_DATA, COMPONENT_CONFIG, COMPONENT_DOMAIN
    from pyaarlo.constant import NIGHTLIGHT_KEY

    mock_spotlight = MagicMock()
    mock_spotlight.is_spotlight = True
    mock_spotlight.is_floodlight = False
    mock_spotlight.name = "Driveway Spotlight"
    mock_spotlight.parent_name = "Driveway"
    mock_spotlight.device_id = "CAM-01"
    mock_spotlight.entity_id = "driveway_spotlight"

    mock_floodlight = MagicMock()
    mock_floodlight.is_spotlight = False
    mock_floodlight.is_floodlight = True
    mock_floodlight.name = "Backyard Floodlight"
    mock_floodlight.parent_name = "Backyard"
    mock_floodlight.device_id = "CAM-02"
    mock_floodlight.entity_id = "backyard_floodlight"

    mock_standalone = MagicMock()
    mock_standalone.is_spotlight = False
    mock_standalone.is_floodlight = False
    mock_standalone.name = "Car Port Light"
    mock_standalone.device_id = "LIGHT-01"
    mock_standalone.entity_id = "car_port_light"

    mock_camera_nl = MagicMock()
    mock_camera_nl.name = "Nursery"
    mock_camera_nl.device_id = "CAM-03"
    mock_camera_nl.entity_id = "nursery"
    mock_camera_nl.has_capability = lambda cap: cap == NIGHTLIGHT_KEY

    mock_camera_normal = MagicMock()
    mock_camera_normal.name = "Driveway"
    mock_camera_normal.device_id = "CAM-01"
    mock_camera_normal.entity_id = "driveway"
    mock_camera_normal.has_capability = lambda cap: False

    mock_arlo = MagicMock()
    mock_arlo.lights = [mock_spotlight, mock_floodlight, mock_standalone]
    mock_arlo.cameras = [mock_camera_nl, mock_camera_normal]

    hass = MagicMock()
    hass.data = {
        COMPONENT_DATA: mock_arlo,
        COMPONENT_CONFIG: {COMPONENT_DOMAIN: {"device_first_naming": True}},
    }

    added = []
    await async_setup_entry(hass, MagicMock(), lambda entities: added.extend(entities))

    assert len(added) == 4
    assert isinstance(added[0], ArloSpotlight)
    assert added[0].suggested_object_id == "aarlo_driveway_spotlight"
    assert isinstance(added[1], ArloFloodLight)
    assert added[1].suggested_object_id == "aarlo_backyard_floodlight"
    assert isinstance(added[2], ArloLight)
    assert added[2].suggested_object_id == "aarlo_car_port_light"
    assert isinstance(added[3], ArloNightLight)
    assert added[3].suggested_object_id == "aarlo_nursery_nightlight"


@pytest.mark.asyncio
async def test_options_flow_switch_step_no_siren_switches():
    from custom_components.aarlo.config_flow import ArloOptionsFlowHandler

    mock_entry = SimpleNamespace(
        options={},
        entry_id="test_entry",
    )
    handler = ArloOptionsFlowHandler(mock_entry)
    handler.hass = SimpleNamespace(config=SimpleNamespace(path=lambda p: f"/tmp/{p}"))

    result = await handler.async_step_switch()
    assert result["type"] == "form"
    assert result["step_id"] == "switch"
    schema_keys = [k.schema if hasattr(k, "schema") else k for k in result["data_schema"].schema.keys()]
    assert "switch_siren" not in schema_keys
    assert "switch_all_sirens" not in schema_keys
    assert "switch_snapshot" in schema_keys
    assert "switch_doorbell_silence" in schema_keys


@pytest.mark.asyncio
async def test_alarm_control_panel_hide_base_stations_with_locations():
    from custom_components.aarlo.alarm_control_panel import (
        async_setup_entry,
        ArloBaseStation,
        ArloLocation,
    )
    from custom_components.aarlo.const import (
        COMPONENT_DATA,
        COMPONENT_CONFIG,
        COMPONENT_DOMAIN,
        COMPONENT_SERVICES,
        CONF_HIDE_BASE_STATION_ALARMS,
    )
    from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
    from datetime import timedelta

    mock_base = MagicMock()
    mock_base.name = "Front"
    mock_base.device_id = "BASE-01"
    mock_base.entity_id = "front"
    mock_base.has_capability = lambda cap: False
    mock_base.attribute = lambda attr, default=None: default

    mock_loc = MagicMock()
    mock_loc.name = "Home"
    mock_loc.device_id = "LOC-01"
    mock_loc.entity_id = "home"
    mock_loc.attribute = lambda attr, default=None: default
    mock_loc.is_armed_away = False
    mock_loc.is_armed_home = False

    mock_arlo = MagicMock()
    mock_arlo.base_stations = [mock_base]
    mock_arlo.locations = [mock_loc]

    # Case 1: hide_base_station_alarms = True (default) -> only Location added
    hass = MagicMock()
    hass.data = {
        COMPONENT_DATA: mock_arlo,
        COMPONENT_CONFIG: {
            COMPONENT_DOMAIN: {CONF_HIDE_BASE_STATION_ALARMS: True},
            ALARM_DOMAIN: {
                "disarmed_mode_name": "disarmed",
                "home_mode_name": "home",
                "away_mode_name": "away",
                "night_mode_name": "night",
                "alarm_volume": 8,
                "trigger_time": timedelta(seconds=30),
                "code": None,
                "code_arm_required": False,
                "code_disarm_required": False,
            },
        },
        COMPONENT_SERVICES: {},
    }
    added_entities_1 = []
    await async_setup_entry(hass, MagicMock(), lambda entities: added_entities_1.extend(entities))
    assert len(added_entities_1) == 1
    assert isinstance(added_entities_1[0], ArloLocation)

    # Case 2: hide_base_station_alarms = False -> both BaseStation and Location added
    hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN][CONF_HIDE_BASE_STATION_ALARMS] = False
    added_entities_2 = []
    await async_setup_entry(hass, MagicMock(), lambda entities: added_entities_2.extend(entities))
    assert len(added_entities_2) == 2
    assert any(isinstance(e, ArloBaseStation) for e in added_entities_2)
    assert any(isinstance(e, ArloLocation) for e in added_entities_2)

    # Case 3: No locations -> BaseStation added regardless
    mock_arlo_no_loc = MagicMock()
    mock_arlo_no_loc.base_stations = [mock_base]
    mock_arlo_no_loc.locations = []
    hass.data[COMPONENT_DATA] = mock_arlo_no_loc
    hass.data[COMPONENT_CONFIG][COMPONENT_DOMAIN][CONF_HIDE_BASE_STATION_ALARMS] = True
    added_entities_3 = []
    await async_setup_entry(hass, MagicMock(), lambda entities: added_entities_3.extend(entities))
    assert len(added_entities_3) == 1
    assert isinstance(added_entities_3[0], ArloBaseStation)


@pytest.mark.asyncio
async def test_location_alarm_entity_naming():
    from custom_components.aarlo.alarm_control_panel import ArloLocation

    mock_user_loc = MagicMock()
    mock_user_loc.name = "user_location_Home"
    mock_user_loc.device_id = "USER-LOC-01"
    mock_user_loc.entity_id = "user_location_home"
    mock_user_loc.attribute = lambda attr, default=None: default

    mock_loc = MagicMock()
    mock_loc.name = "location_Home"
    mock_loc.device_id = "LOC-01"
    mock_loc.entity_id = "location_home"
    mock_loc.attribute = lambda attr, default=None: default

    config = {
        "disarmed_mode_name": "disarmed",
        "home_mode_name": "home",
        "away_mode_name": "away",
        "night_mode_name": "night",
        "alarm_volume": 8,
        "trigger_time": 30,
        "code": None,
        "code_arm_required": False,
        "code_disarm_required": False,
    }

    panel_user = ArloLocation(mock_user_loc, {"add_aarlo_prefix": True}, config)
    assert panel_user.name == "User Location Home"
    assert panel_user._attr_has_entity_name is False
    assert panel_user.device_info["name"] == "User Location Home"
    assert panel_user.suggested_object_id == "aarlo_user_location_home"
    assert panel_user.entity_id == "alarm_control_panel.aarlo_user_location_home"

    panel_loc = ArloLocation(mock_loc, {"add_aarlo_prefix": True}, config)
    assert panel_loc.name == "Location Home"
    assert panel_loc._attr_has_entity_name is False
    assert panel_loc.device_info["name"] == "Location Home"
    assert panel_loc.suggested_object_id == "aarlo_location_home"
    assert panel_loc.entity_id == "alarm_control_panel.aarlo_location_home"


@pytest.mark.asyncio
async def test_config_flow_configurable_title():
    from custom_components.aarlo.config_flow import AarloFlowHandler
    from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
    from custom_components.aarlo.const import CONF_TFA_TYPE, CONF_ADD_AARLO_PREFIX, CONF_DEVICE_FIRST_NAMING

    handler = AarloFlowHandler()
    handler.hass = MagicMock()
    handler._async_current_entries = lambda: []

    # Verify form schema includes CONF_DEVICE_FIRST_NAMING
    form = await handler.async_step_user(None)
    assert form["type"] == "form"
    schema_keys = [k.schema if hasattr(k, "schema") else k for k in form["data_schema"].schema.keys()]
    assert CONF_DEVICE_FIRST_NAMING in schema_keys
    assert CONF_ADD_AARLO_PREFIX in schema_keys

    # Case 1: Custom name and legacy device naming specified
    res1 = await handler.async_step_user({
        CONF_NAME: "My Custom Arlo",
        CONF_USERNAME: "user@example.com",
        CONF_PASSWORD: "secretpassword",
        CONF_TFA_TYPE: "NONE",
        CONF_ADD_AARLO_PREFIX: True,
        CONF_DEVICE_FIRST_NAMING: False,
    })
    assert res1["type"] == "create_entry"
    assert res1["title"] == "My Custom Arlo"
    assert res1["data"][CONF_DEVICE_FIRST_NAMING] is False

    # Case 2: No custom name specified -> defaults to "Aarlo for <email>", device_first defaults to True
    handler2 = AarloFlowHandler()
    handler2.hass = MagicMock()
    handler2._async_current_entries = lambda: []
    res2 = await handler2.async_step_user({
        CONF_NAME: "",
        CONF_USERNAME: "other@example.com",
        CONF_PASSWORD: "secretpassword",
        CONF_TFA_TYPE: "NONE",
        CONF_ADD_AARLO_PREFIX: True,
        CONF_DEVICE_FIRST_NAMING: True,
    })
    assert res2["type"] == "create_entry"
    assert res2["title"] == "Aarlo for other@example.com"
    assert res2["data"][CONF_DEVICE_FIRST_NAMING] is True
