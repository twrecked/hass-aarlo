"""Config flow for Aarlo"""

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import callback
from homeassistant.helpers.selector import selector, SelectOptionDict, \
    SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    COMPONENT_CONFIG,
    CONF_TFA_HOST,
    CONF_TFA_PASSWORD,
    CONF_TFA_SOURCE,
    CONF_TFA_TYPE,
    CONF_TFA_USERNAME,
    DOMAIN,
)
from .cfg import UpgradeCfg

_LOGGER = logging.getLogger(__name__)

DEFAULT_IMPORTED_NAME = "imported"

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


class AarloFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Aarlo config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ArloOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self.username = None
        self.password = None
        self.tfaUsername = ""
        self.tfaPassword = ""
        self.tfaHost = ""

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
                CONF_TFA_TYPE: "none"
            }

            # Lets look at what we have.
            _LOGGER.debug(f"info={info}")
            if info["tfa_type"] == "NONE":
                config.update({
                    CONF_TFA_TYPE: "none"
                })

            elif info["tfa_type"] == "PUSH":
                config.update({
                    CONF_TFA_TYPE: "push",
                    CONF_TFA_SOURCE: "push",
                })

            elif info["tfa_type"] == "IMAP":
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

            elif info["tfa_type"] == "RESTAPI":
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
                _LOGGER.debug(f"config={config}")

        data_schema = {
            vol.Required(CONF_USERNAME, default=self.username): str,
            vol.Required(CONF_PASSWORD, default=self.password): str,
            vol.Required("tfa_type",
                         # description={"suggested_value": "IMAP"},
                         default="IMAP"): TFA_SELECTOR,
            vol.Optional(CONF_TFA_USERNAME, default=self.tfaUsername): str,
            vol.Optional(CONF_TFA_PASSWORD, default=self.tfaPassword): str,
            vol.Optional(CONF_TFA_HOST, default=self.tfaHost): str,
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
            title=f"Aarlo Config for {data[CONF_USERNAME]} (imported)",
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
            self._config = user_input
            return await self.async_step_binary_sensor(None)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="alarm_control_panel",
            data_schema=vol.Schema({
                vol.Required("alarm_control_panel_disarmed_mode_name",
                             default=options.get("alarm_control_panel_disarmed_mode_name", True)): str,
                vol.Required("alarm_control_panel_home_mode_name",
                             default=options.get("alarm_control_panel_home_mode_name", True)): str,
                vol.Required("alarm_control_panel_away_mode_name",
                             default=options.get("alarm_control_panel_away_mode_name", True)): str,
                vol.Required("alarm_control_panel_night_mode_name",
                             default=options.get("alarm_control_panel_night_mode_name", True)): str,
                vol.Required("alarm_control_panel_code_arm_required",
                             default=options.get("alarm_control_panel_code_arm_required", True)): bool,
                vol.Required("alarm_control_panel_code_disarm_required",
                             default=options.get("alarm_control_panel_code_disarm_required", True)): bool,
                vol.Required("alarm_control_panel_trigger_time",
                             default=options.get("alarm_control_panel_trigger_time", True)): int,
                vol.Required("alarm_control_panel_alarm_volume",
                             default=options.get("alarm_control_panel_alarm_volume", True)): int,
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
            _LOGGER.debug(f"_config={self._config}")
            return self.async_create_entry(title="", data=self._config)

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
