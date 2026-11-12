"""Config flow for Aarlo"""

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectOptionDict, \
    SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    CONF_DEVICE_FIRST_NAMING,
    CONF_ADD_AARLO_PREFIX,
    CONF_HIDE_BASE_STATION_ALARMS,
    DEFAULT_HIDE_BASE_STATION_ALARMS,
    CONF_TFA_HOST,
    CONF_TFA_PASSWORD,
    CONF_TFA_SOURCE,
    CONF_TFA_TYPE,
    CONF_TFA_USERNAME,
    COMPONENT_DOMAIN,
    STATE_ALARM_ARLO_ARMED,
    STATE_ALARM_ARLO_DISARMED,
    STATE_ALARM_ARLO_HOME,
    STATE_ALARM_ARLO_NIGHT
)
from .cfg import UpgradeCfg, _async_load_yaml, _default_config_file


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

BACKEND_TYPES = [
    SelectOptionDict(value="auto", label="Auto (MQTT with fallback)"),
    SelectOptionDict(value="mqtt", label="MQTT (WebSockets)"),
    SelectOptionDict(value="sse", label="SSE (Server-Sent Events)"),
]
BACKEND_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=BACKEND_TYPES,
        mode=SelectSelectorMode.DROPDOWN,
    )
)

HTTP_BACKEND_TYPES = [
    SelectOptionDict(value="curl_cffi", label="curl_cffi (Chrome TLS fingerprint)"),
    SelectOptionDict(value="cloudscraper", label="cloudscraper (Cloudflare scraper)"),
    SelectOptionDict(value="requests", label="requests (Standard HTTP)"),
]
HTTP_BACKEND_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=HTTP_BACKEND_TYPES,
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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._name: str = ""
        self._username: str = ""
        self._password: str = ""
        self._tfa_username: str = ""
        self._tfa_password: str = ""
        self._tfa_host: str = ""
        self._add_prefix: bool = True
        self._reauth_entry: config_entries.ConfigEntry | None = None
        self._reconfigure_entry: config_entries.ConfigEntry | None = None

    def _get_entry(self) -> config_entries.ConfigEntry | None:
        """Get the target config entry for reauth or reconfigure."""
        if getattr(self, "_reauth_entry", None) is not None:
            return self._reauth_entry
        if getattr(self, "_reconfigure_entry", None) is not None:
            return self._reconfigure_entry
        if hasattr(self, "_get_reauth_entry"):
            try:
                return self._get_reauth_entry()
            except Exception:
                pass
        if hasattr(self, "_get_reconfigure_entry"):
            try:
                return self._get_reconfigure_entry()
            except Exception:
                pass
        entry_id = self.context.get("entry_id")
        if entry_id and hasattr(self, "hass") and self.hass:
            return self.hass.config_entries.async_get_entry(entry_id)
        entries = self._async_current_entries()
        return entries[0] if entries else None

    @staticmethod
    def _process_flow_input(info: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        """Transform raw UI form input into persisted entry data."""
        errors: dict[str, str] = {}
        config: dict[str, Any] = {
            CONF_USERNAME: info[CONF_USERNAME],
            CONF_PASSWORD: info[CONF_PASSWORD],
            CONF_TFA_TYPE: "none",
            CONF_ADD_AARLO_PREFIX: info.get(CONF_ADD_AARLO_PREFIX, True),
            CONF_DEVICE_FIRST_NAMING: info.get(CONF_DEVICE_FIRST_NAMING, True),
        }

        tfa_choice = info.get(CONF_TFA_TYPE, "NONE")
        if tfa_choice == "NONE":
            config.update({
                CONF_TFA_TYPE: "none",
                "tfa": "none",
            })
        elif tfa_choice == "PUSH":
            config.update({
                CONF_TFA_TYPE: "push",
                CONF_TFA_SOURCE: "push",
                "tfa": "push",
            })
        elif tfa_choice == "IMAP":
            if (not info.get(CONF_TFA_USERNAME) or not info.get(CONF_TFA_PASSWORD)
                    or not info.get(CONF_TFA_HOST)):
                errors["base"] = "missing_imap_fields"
            else:
                config.update({
                    CONF_TFA_TYPE: "email",
                    CONF_TFA_SOURCE: "imap",
                    "tfa": "email:imap",
                    CONF_TFA_HOST: info[CONF_TFA_HOST],
                    CONF_TFA_USERNAME: info[CONF_TFA_USERNAME],
                    CONF_TFA_PASSWORD: info[CONF_TFA_PASSWORD],
                })
        elif tfa_choice == "RESTAPI":
            if (not info.get(CONF_TFA_USERNAME) or not info.get(CONF_TFA_PASSWORD)
                    or not info.get(CONF_TFA_HOST)):
                errors["base"] = "missing_restapi_fields"
            else:
                config.update({
                    CONF_TFA_TYPE: "sms",
                    CONF_TFA_SOURCE: "rest-api",
                    "tfa": "sms",
                    CONF_TFA_HOST: info[CONF_TFA_HOST],
                    CONF_TFA_USERNAME: info[CONF_TFA_USERNAME],
                    CONF_TFA_PASSWORD: info[CONF_TFA_PASSWORD],
                })

        return config, errors

    async def async_step_user(self, info: dict | None = None):
        """Handle user initiated flow."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if info is not None:
            config, errors = self._process_flow_input(info)

            # Looks good, then create it.
            if not errors:
                _LOGGER.debug(f"aarlo-config={config}")
                name = info.get(CONF_NAME, "").strip() if isinstance(info.get(CONF_NAME), str) else ""
                title = name if name else f"Aarlo for {info[CONF_USERNAME]}"
                return self.async_create_entry(
                    title=title,
                    data=config
                )

            # Pass broken one into the GUI.
            self._name = info.get(CONF_NAME, "")
            self._username = info[CONF_USERNAME]
            self._password = info[CONF_PASSWORD]
            self._tfa_username = info.get(CONF_TFA_USERNAME, "")
            self._tfa_password = info.get(CONF_TFA_PASSWORD, "")
            self._tfa_host = info.get(CONF_TFA_HOST, "")
            self._add_prefix = info.get(CONF_ADD_AARLO_PREFIX, True)

        data_schema = {
            vol.Optional(CONF_NAME, default=self._name): str,
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> Any:
        """Handle initiated reauth flow."""
        self._reauth_entry = self._get_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> Any:
        """Confirm reauth dialog to update password."""
        entry = self._get_entry()
        if not entry:
            return self.async_abort(reason="reauth_failed")

        errors: dict[str, str] = {}
        if user_input is not None:
            new_data = dict(entry.data)
            new_data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            if user_input.get(CONF_TFA_PASSWORD):
                new_data[CONF_TFA_PASSWORD] = user_input[CONF_TFA_PASSWORD]

            if hasattr(self, "async_update_reload_and_abort"):
                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                    reason="reauth_successful",
                )
            if hasattr(self, "hass") and self.hass:
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_PASSWORD): str,
        }
        tfa_raw = str(entry.data.get("tfa") or entry.data.get(CONF_TFA_TYPE, "")).lower()
        if tfa_raw in ("email", "email:imap", "imap"):
            schema_dict[vol.Optional(CONF_TFA_PASSWORD, default=entry.data.get(CONF_TFA_PASSWORD, ""))] = str

        username = entry.data.get(CONF_USERNAME, "")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle voluntary reconfiguration of credentials and TFA settings."""
        entry = self._get_entry()
        if not entry:
            return self.async_abort(reason="reconfigure_failed")

        errors: dict[str, str] = {}
        if user_input is not None:
            config, errors = self._process_flow_input(user_input)
            if not errors:
                new_data = dict(entry.data)
                new_data.update(config)
                if hasattr(self, "async_update_reload_and_abort"):
                    return self.async_update_reload_and_abort(
                        entry,
                        data=new_data,
                        reason="reconfigure_successful",
                    )
                if hasattr(self, "hass") and self.hass:
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        # Map existing TFA to selector value
        tfa_type_val = "IMAP"
        tfa_raw = str(entry.data.get("tfa") or entry.data.get(CONF_TFA_TYPE, "")).lower()
        if tfa_raw in ("none",):
            tfa_type_val = "NONE"
        elif tfa_raw in ("push",):
            tfa_type_val = "PUSH"
        elif tfa_raw in ("sms", "rest-api", "restapi"):
            tfa_type_val = "RESTAPI"
        elif tfa_raw in ("email", "email:imap", "imap"):
            tfa_type_val = "IMAP"

        data_schema = {
            vol.Required(CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=entry.data.get(CONF_PASSWORD, "")): str,
            vol.Required(CONF_TFA_TYPE, default=tfa_type_val): TFA_SELECTOR,
            vol.Optional(CONF_TFA_USERNAME, default=entry.data.get(CONF_TFA_USERNAME, "")): str,
            vol.Optional(CONF_TFA_PASSWORD, default=entry.data.get(CONF_TFA_PASSWORD, "")): str,
            vol.Optional(CONF_TFA_HOST, default=entry.data.get(CONF_TFA_HOST, "")): str,
            vol.Required(CONF_ADD_AARLO_PREFIX, default=entry.data.get(CONF_ADD_AARLO_PREFIX, True)): bool,
        }

        username = entry.data.get(CONF_USERNAME, "")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(data_schema),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_import(self, import_data):
        """Import momentary config from configuration.yaml."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        _LOGGER.info("importing aarlo YAML")
        await UpgradeCfg.create_file_config(self.hass, import_data)
        data = UpgradeCfg.create_flow_data(import_data)
        options = UpgradeCfg.create_flow_options(import_data)

        name = import_data.get(CONF_NAME, "").strip() if isinstance(import_data.get(CONF_NAME), str) else ""
        title = name if name else f"Aarlo for {data[CONF_USERNAME]} (imported)"
        return self.async_create_entry(
            title=title,
            data=data,
            options=options
        )


class ArloOptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._config: dict[str, Any] = {}

    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        return await self.async_step_general(user_input)

    async def async_step_general(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage backend and media options."""
        if user_input is not None:
            _LOGGER.debug(f"user-input-general={user_input}")
            self._config.update(user_input)
            return await self.async_step_alarm_control_panel(None)

        options = dict(self._config_entry.options)
        yaml_config = await _async_load_yaml(self.hass, _default_config_file(self.hass))
        aarlo_yaml = yaml_config.get(COMPONENT_DOMAIN, {})

        backend_default = options.get("backend", aarlo_yaml.get("backend", "auto"))
        http_backend_default = options.get("http_backend", aarlo_yaml.get("http_backend", "curl_cffi"))
        save_media_default = options.get("save_media_to", aarlo_yaml.get("save_media_to", ""))
        media_retention_default = options.get("media_retention_days", aarlo_yaml.get("media_retention_days", 0))
        entry_data = getattr(self._config_entry, "data", {})
        device_first_default = options.get(CONF_DEVICE_FIRST_NAMING, aarlo_yaml.get(CONF_DEVICE_FIRST_NAMING, entry_data.get(CONF_DEVICE_FIRST_NAMING, False)))
        hide_base_station_alarms_default = options.get(
            CONF_HIDE_BASE_STATION_ALARMS,
            aarlo_yaml.get(
                CONF_HIDE_BASE_STATION_ALARMS,
                entry_data.get(CONF_HIDE_BASE_STATION_ALARMS, DEFAULT_HIDE_BASE_STATION_ALARMS),
            ),
        )

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema({
                vol.Required("backend", default=backend_default): BACKEND_SELECTOR,
                vol.Required("http_backend", default=http_backend_default): HTTP_BACKEND_SELECTOR,
                vol.Optional("save_media_to", default=save_media_default): str,
                vol.Optional("media_retention_days", default=media_retention_default): int,
                vol.Optional(CONF_DEVICE_FIRST_NAMING, default=device_first_default): bool,
                vol.Optional(CONF_HIDE_BASE_STATION_ALARMS, default=hide_base_station_alarms_default): bool,
            })
        )

    async def async_step_alarm_control_panel(
            self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-alarm={user_input}")

            # Yuck.
            if user_input.get("alarm_control_panel_code") == "no code needed":
                user_input.pop("alarm_control_panel_code")

            self._config.update(user_input)
            return await self.async_step_binary_sensor(None)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="alarm_control_panel",
            data_schema=vol.Schema({
                vol.Optional("alarm_control_panel_code",
                             default=options.get("alarm_control_panel_code", "no code needed")): str,
                vol.Optional("alarm_control_panel_disarmed_mode_name",
                             default=options.get("alarm_control_panel_disarmed_mode_name",
                                                 STATE_ALARM_ARLO_DISARMED)): str,
                vol.Optional("alarm_control_panel_home_mode_name",
                             default=options.get("alarm_control_panel_home_mode_name",
                                                 STATE_ALARM_ARLO_HOME)): str,
                vol.Optional("alarm_control_panel_away_mode_name",
                             default=options.get("alarm_control_panel_away_mode_name",
                                                 STATE_ALARM_ARLO_ARMED)): str,
                vol.Optional("alarm_control_panel_night_mode_name",
                             default=options.get("alarm_control_panel_night_mode_name",
                                                 STATE_ALARM_ARLO_NIGHT)): str,
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
    ) -> config_entries.ConfigFlowResult:

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
    ) -> config_entries.ConfigFlowResult:

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
    ) -> config_entries.ConfigFlowResult:

        if user_input is not None:
            _LOGGER.debug(f"user-input-switch={user_input}")
            self._config.update(user_input)
            _LOGGER.debug(f"_config={self._config}")
            return self.async_create_entry(title="", data=self._config)

        options = self._config_entry.options
        return self.async_show_form(
            step_id="switch",
            data_schema=vol.Schema({
                vol.Required("switch_snapshot",
                             default=options.get("switch_snapshot", True)): bool,
                vol.Required("switch_snapshot_timeout",
                             default=options.get("switch_snapshot_timeout", 15)): int,
                vol.Required("switch_doorbell_silence",
                             default=options.get("switch_doorbell_silence", True)): bool,
            })
        )
