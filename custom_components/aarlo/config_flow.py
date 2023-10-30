"""Config flow for Aarlo"""

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectOptionDict, \
    SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    COMPONENT_CONFIG,
    CONF_ADD_AARLO_PREFIX,
    CONF_TFA_HOST,
    CONF_TFA_PASSWORD,
    CONF_TFA_SOURCE,
    CONF_TFA_TYPE,
    CONF_TFA_USERNAME,
    COMPONENT_DOMAIN,
)
from .cfg import UpgradeCfg

_LOGGER = logging.getLogger(__name__)

DEFAULT_IMPORTED_NAME = "imported"

# TFA types. We actually map these to the correct source/type pairing.
TFA_TYPES = [
    SelectOptionDict(value="NONE", label="None"),
    SelectOptionDict(value="IMAP", label="IMAP"),
    SelectOptionDict(value="PUSH", label="PUSH"),
    SelectOptionDict(value="RESTAPI", label="RESTAPI"),
]
TFA_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=TFA_TYPES,
        mode=SelectSelectorMode.DROPDOWN,
    )
)


class AarloFlowHandler(config_entries.ConfigFlow, domain=COMPONENT_DOMAIN):
    """Aarlo config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ArloOptionsFlowHandler(config_entry)

    _username: str = ""
    _password: str = ""
    _tfa_username: str = ""
    _tfa_password: str = ""
    _tfa_host: str = ""
    _add_prefix: bool = True

    def __init__(self):
        """Initialize the config flow."""

    async def async_step_user(self, info: dict = None):
        """Handle user initiated flow."""

        if self.hass.data.get(COMPONENT_CONFIG):
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if info is not None:

            # applies to all
            config = {
                CONF_USERNAME: info[CONF_USERNAME],
                CONF_PASSWORD: info[CONF_PASSWORD],
                CONF_TFA_TYPE: "none",
                CONF_ADD_AARLO_PREFIX: info[CONF_ADD_AARLO_PREFIX]
            }

            # Lets look at what we have.
            _LOGGER.debug(f"info={info}")
            if info[CONF_TFA_TYPE] == "NONE":
                config.update({
                    CONF_TFA_TYPE: "none"
                })

            elif info[CONF_TFA_TYPE] == "PUSH":
                config.update({
                    CONF_TFA_TYPE: "push",
                    CONF_TFA_SOURCE: "push",
                })

            elif info[CONF_TFA_TYPE] == "IMAP":
                if (not info[CONF_TFA_USERNAME] or not info[CONF_TFA_PASSWORD]
                        or not info[CONF_TFA_HOST]):
                    errors["base"] = "missing_imap_fields"
                else:
                    config.update({
                        CONF_TFA_TYPE: "email",
                        CONF_TFA_SOURCE: "imap",
                        CONF_TFA_HOST: info[CONF_TFA_HOST],
                        CONF_TFA_USERNAME: info[CONF_TFA_USERNAME],
                        CONF_TFA_PASSWORD: info[CONF_TFA_PASSWORD],
                    })

            elif info[CONF_TFA_TYPE] == "RESTAPI":
                if (not info[CONF_TFA_USERNAME] or not info[CONF_TFA_PASSWORD]
                        or not info[CONF_TFA_HOST]):
                    errors["base"] = "missing_restapi_fields"
                config.update({
                    CONF_TFA_TYPE: "SMS",
                    CONF_TFA_SOURCE: "rest-api",
                    CONF_TFA_HOST: info[CONF_TFA_HOST],
                    CONF_TFA_USERNAME: info[CONF_TFA_USERNAME],
                    CONF_TFA_PASSWORD: info[CONF_TFA_PASSWORD],
                })

            # Looks good, then create it.
            if not errors:
                _LOGGER.debug(f"aarlo-config={config}")
                return self.async_create_entry(
                    title=f"Aarlo for ${self._username}",
                    data=config
                )

            # Pass broken one into the GUI.
            self._username: str = info[CONF_USERNAME]
            self._password: str = info[CONF_PASSWORD]
            self._tfa_username: str = info.get(CONF_TFA_USERNAME, "")
            self._tfa_password: str = info.get(CONF_TFA_PASSWORD, "")
            self._tfa_host: str = info.get(CONF_TFA_HOST, "")
            self._add_prefix: bool = info[CONF_ADD_AARLO_PREFIX]

        data_schema = {
            vol.Required(CONF_USERNAME, default=self._username): str,
            vol.Required(CONF_PASSWORD, default=self._password): str,
            vol.Required(CONF_TFA_TYPE, default="IMAP"): TFA_SELECTOR,
            vol.Optional(CONF_TFA_USERNAME, default=self._tfa_username): str,
            vol.Optional(CONF_TFA_PASSWORD, default=self._tfa_password): str,
            vol.Optional(CONF_TFA_HOST, default=self._tfa_host): str,
            vol.Required(CONF_ADD_AARLO_PREFIX, default=self._add_prefix): bool,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_import(self, import_data):
        """Import momentary config from configuration.yaml."""

        _LOGGER.info("importing aarlo YAML")
        UpgradeCfg.create_file_config(import_data)
        data = UpgradeCfg.create_flow_data(import_data)
        options = UpgradeCfg.create_flow_options(import_data)

        return self.async_create_entry(
            title=f"Aarlo for {data[CONF_USERNAME]} (imported)",
            data=data,
            options=options
        )


class ArloOptionsFlowHandler(config_entries.OptionsFlow):

    _config: dict[str, Any] = {}

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        return await self.async_step_alarm_control_panel(user_input)

    async def async_step_alarm_control_panel(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-alarm={user_input}")

            # Yuck.
            if user_input["alarm_control_panel_code"] == "no code needed":
                user_input.pop("alarm_control_panel_code")

            self._config = user_input
            return await self.async_step_binary_sensor(None)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="alarm_control_panel",
            data_schema=vol.Schema({
                vol.Optional("alarm_control_panel_code",
                             default=options.get("alarm_control_panel_code", "no code needed")): str,
                vol.Optional("alarm_control_panel_disarmed_mode_name",
                             default=options.get("alarm_control_panel_disarmed_mode_name", "disarmed")): str,
                vol.Optional("alarm_control_panel_home_mode_name",
                             default=options.get("alarm_control_panel_home_mode_name", "home")): str,
                vol.Optional("alarm_control_panel_away_mode_name",
                             default=options.get("alarm_control_panel_away_mode_name", "away")): str,
                vol.Optional("alarm_control_panel_night_mode_name",
                             default=options.get("alarm_control_panel_night_mode_name", "night")): str,
                vol.Optional("alarm_control_panel_code_arm_required",
                             default=options.get("alarm_control_panel_code_arm_required", False)): bool,
                vol.Optional("alarm_control_panel_code_disarm_required",
                             default=options.get("alarm_control_panel_code_disarm_required", False)): bool,
                vol.Optional("alarm_control_panel_trigger_time",
                             default=options.get("alarm_control_panel_trigger_time", 60)): int,
                vol.Optional("alarm_control_panel_alarm_volume",
                             default=options.get("alarm_control_panel_alarm_volume", 3)): int,
                # vol.Required("alarm_control_panel_command_template",
                #              default=options.get("alarm_control_panel_command_template", True)): str,
            })
        )

    async def async_step_binary_sensor(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-binary-sensor={user_input}")
            self._config.update(user_input)
            return await self.async_step_sensor(None)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="binary_sensor",
            data_schema=vol.Schema({
                vol.Required("binary_sensor_sound",
                             default=options.get("binary_sensor_sound", True)): bool,
                vol.Required("binary_sensor_motion",
                             default=options.get("binary_sensor_motion", True)): bool,
                vol.Required("binary_sensor_ding",
                             default=options.get("binary_sensor_ding", True)): bool,
                vol.Required("binary_sensor_cry",
                             default=options.get("binary_sensor_cry", True)): bool,
                vol.Required("binary_sensor_connectivity",
                             default=options.get("binary_sensor_connectivity", True)): bool,
                vol.Required("binary_sensor_contact",
                             default=options.get("binary_sensor_contact", True)): bool,
                vol.Required("binary_sensor_light",
                             default=options.get("binary_sensor_light", True)): bool,
                vol.Required("binary_sensor_tamper",
                             default=options.get("binary_sensor_tamper", True)): bool,
                vol.Required("binary_sensor_leak",
                             default=options.get("binary_sensor_leak", True)): bool,
            }),
        )

    async def async_step_sensor(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-sensor={user_input}")
            self._config.update(user_input)
            return await self.async_step_switch(None)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="sensor",
            data_schema=vol.Schema({
                vol.Required("sensor_last_capture",
                             default=options.get("sensor_last_capture", True)): bool,
                vol.Required("sensor_total_cameras",
                             default=options.get("sensor_total_cameras", True)): bool,
                vol.Required("sensor_recent_activity",
                             default=options.get("sensor_recent_activity", True)): bool,
                vol.Required("sensor_captured_today",
                             default=options.get("sensor_captured_today", True)): bool,
                vol.Required("sensor_battery_level",
                             default=options.get("sensor_battery_level", True)): bool,
                vol.Required("sensor_signal_strength",
                             default=options.get("sensor_signal_strength", True)): bool,
                vol.Required("sensor_temperature",
                             default=options.get("sensor_temperature", True)): bool,
                vol.Required("sensor_humidity",
                             default=options.get("sensor_humidity", True)): bool,
                vol.Required("sensor_air_quality",
                             default=options.get("sensor_air_quality", True)): bool,
            }),
        )

    async def async_step_switch(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-switch={user_input}")
            self._config.update(user_input)
            _LOGGER.debug(f"_config={self._config}")
            return self.async_create_entry(title="", data=self._config)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="switch",
            data_schema=vol.Schema({
                vol.Required("switch_siren",
                             default=options.get("switch_siren", True)): bool,
                vol.Required("switch_all_sirens",
                             default=options.get("switch_all_sirens", True)): bool,
                vol.Required("switch_siren_allow_off",
                             default=options.get("switch_siren_allow_off", True)): bool,
                vol.Required("switch_siren_volume",
                             default=options.get("switch_siren_volume", 3)): int,
                vol.Required("switch_siren_duration",
                             default=options.get("switch_siren_duration", 10)): int,
                vol.Required("switch_snapshot",
                             default=options.get("switch_snapshot", True)): bool,
                vol.Required("switch_snapshot_timeout",
                             default=options.get("switch_snapshot_timeout", 15)): int,
                vol.Required("switch_doorbell_silence",
                             default=options.get("switch_doorbell_silence", True)): bool,
            })
        )
