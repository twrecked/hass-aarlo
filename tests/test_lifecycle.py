"""Lifecycle regressions using synthetic data and no Arlo network access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.aarlo import async_unload_entry
from custom_components.aarlo.config_flow import AarloFlowHandler
from custom_components.aarlo.const import (
    COMPONENT_CONFIG,
    COMPONENT_DATA,
    COMPONENT_SERVICES,
)


def make_hass(data, unload_ok=True):
    return SimpleNamespace(
        data=data,
        config_entries=SimpleNamespace(
            async_unload_platforms=AsyncMock(return_value=unload_ok)
        ),
        async_add_executor_job=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_unload_stops_client_before_removing_data():
    client = MagicMock()
    data = {COMPONENT_DATA: client, COMPONENT_CONFIG: {}, COMPONENT_SERVICES: {}}
    hass = make_hass(data)

    async def run_executor(func, logout):
        assert data[COMPONENT_DATA] is client
        func(logout)

    hass.async_add_executor_job.side_effect = run_executor
    assert await async_unload_entry(hass, SimpleNamespace(title="Test"))
    client.stop.assert_called_once_with(True)
    assert data == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("remaining", [[], [COMPONENT_CONFIG], [COMPONENT_SERVICES],
                                    [COMPONENT_CONFIG, COMPONENT_SERVICES]])
async def test_unload_without_client_cleans_remaining_runtime_data(remaining):
    data = {key: {} for key in remaining}
    data["unrelated"] = "preserve"
    hass = make_hass(data)

    assert await async_unload_entry(hass, SimpleNamespace(title="Test"))
    assert data == {"unrelated": "preserve"}
    hass.async_add_executor_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_unload_with_client_and_missing_metadata():
    client = MagicMock()
    hass = make_hass({COMPONENT_DATA: client})
    assert await async_unload_entry(hass, SimpleNamespace(title="Test"))
    hass.async_add_executor_job.assert_awaited_once_with(client.stop, True)
    assert hass.data == {}


@pytest.mark.asyncio
async def test_failed_platform_unload_preserves_runtime():
    client = MagicMock()
    data = {COMPONENT_DATA: client, COMPONENT_CONFIG: {}, COMPONENT_SERVICES: {}}
    hass = make_hass(data, unload_ok=False)
    original = data.copy()

    assert not await async_unload_entry(hass, SimpleNamespace(title="Test"))
    assert data == original
    hass.async_add_executor_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_stop_error_is_not_hidden_and_preserves_runtime():
    client = MagicMock()
    data = {COMPONENT_DATA: client, COMPONENT_CONFIG: {}, COMPONENT_SERVICES: {}}
    hass = make_hass(data)
    original = data.copy()
    hass.async_add_executor_job.side_effect = RuntimeError("stop failed")

    with pytest.raises(RuntimeError, match="stop failed"):
        await async_unload_entry(hass, SimpleNamespace(title="Test"))
    assert data == original


@pytest.mark.asyncio
async def test_repeated_unload_stops_client_only_once():
    client = MagicMock()
    hass = make_hass({COMPONENT_DATA: client, COMPONENT_CONFIG: {}, COMPONENT_SERVICES: {}})
    entry = SimpleNamespace(title="Test")
    assert await async_unload_entry(hass, entry)
    assert await async_unload_entry(hass, entry)
    hass.async_add_executor_job.assert_awaited_once_with(client.stop, True)


@pytest.mark.asyncio
@pytest.mark.parametrize("step", ["user", "import"])
@pytest.mark.parametrize("state", ["setup_error", "setup_retry", "not_loaded", "failed_unload"])
async def test_existing_entry_blocks_duplicate_even_without_runtime(step, state):
    flow = AarloFlowHandler()
    flow.hass = SimpleNamespace(data={})
    existing = SimpleNamespace(state=state)
    user_input = {
        "username": "test@example.invalid",
        "password": "synthetic-test-password",
        "tfa_type": "NONE",
        "add_aarlo_prefix": True,
    }
    with (
        patch.object(flow, "_async_current_entries", return_value=[existing]),
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_file_config",
              new_callable=AsyncMock) as write_config,
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_flow_data",
              return_value={"username": "test@example.invalid"}),
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_flow_options",
              return_value={}),
    ):
        result = await getattr(flow, f"async_step_{step}")(user_input)
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"
    write_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_first_user_flow_still_shows_form():
    flow = AarloFlowHandler()
    flow.hass = SimpleNamespace(data={})
    with patch.object(flow, "_async_current_entries", return_value=[]):
        result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_first_import_still_creates_entry():
    flow = AarloFlowHandler()
    flow.hass = SimpleNamespace(data={})
    with (
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_file_config",
              new_callable=AsyncMock) as write_config,
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_flow_data",
              return_value={"username": "test@example.invalid"}),
        patch("custom_components.aarlo.config_flow.UpgradeCfg.create_flow_options",
              return_value={}),
    ):
        result = await flow.async_step_import({})
    assert result["type"] == "create_entry"
    write_config.assert_awaited_once()
