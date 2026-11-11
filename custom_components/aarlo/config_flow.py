"""Config flow for Aarlo"""

import asyncio
import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectOptionDict, \
    SelectSelector, SelectSelectorConfig, SelectSelectorMode

try:
    from pyaarlo import ArloLogin, LoginStep
except ImportError:  # pragma: no cover - pyaarlo without the step by step login
    ArloLogin = None  # type: ignore[assignment, misc]
    LoginStep = None  # type: ignore[assignment, misc]

from .const import (
    CONF_ADD_AARLO_PREFIX,
    CONF_TFA_FACTOR_ID,
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
from .cfg import BlendedCfg, PyaarloCfg, UpgradeCfg, _async_load_yaml, _default_config_file


_LOGGER = logging.getLogger(__name__)

DEFAULT_IMPORTED_NAME = "imported"
CONF_MANUAL_TFA = "manual_tfa"
CONF_FACTOR_ID = "factor_id"
CONF_CODE = "code"

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


def _factor_label(factor: dict[str, Any]) -> str:
    name = factor.get("displayName") or factor.get("factorNickname") or factor.get("factorId", "?")
    kind = str(factor.get("factorType", "?"))
    if kind.upper() == "PUSH":
        kind = "Arlo app"
    elif kind.upper() == "SMS":
        kind = "SMS"
    else:
        kind = kind.title()
    return f"{name} ({kind})"


def _factor_selector(factors: list[dict[str, Any]]) -> SelectSelector:
    """A picker built from the account's real factors, so the user picks
    "Pixel 9" or "home@example.com" instead of guessing a mechanism.
    """
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=factor["factorId"], label=_factor_label(factor))
                for factor in factors
            ],
            mode=SelectSelectorMode.LIST,
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
        self._username: str = ""
        self._password: str = ""
        self._tfa_username: str = ""
        self._tfa_password: str = ""
        self._tfa_host: str = ""
        self._add_prefix: bool = True
        self._reauth_entry: config_entries.ConfigEntry | None = None
        self._reconfigure_entry: config_entries.ConfigEntry | None = None

        # State for the step by step login, see `async_step_user`.
        self._login: Any = None
        self._factor: dict[str, Any] | None = None
        self._push_task: asyncio.Task[Any] | None = None
        self._flow_error: str | None = None

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

    def _base_config(self) -> dict[str, Any]:
        return {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_ADD_AARLO_PREFIX: self._add_prefix,
        }

    async def _async_close_login(self) -> None:
        if self._push_task is not None and not self._push_task.done():
            self._push_task.cancel()
        self._push_task = None
        if self._login is not None:
            try:
                await self._login.close()
            except Exception as e:
                _LOGGER.debug(f"aarlo-login-close-failed={e}")
        self._login = None

    async def _async_create_login_entry(self, config: dict[str, Any]):
        await self._async_close_login()
        config = {**self._base_config(), **config}
        _LOGGER.debug(f"aarlo-config={ {k: v for k, v in config.items() if k != CONF_PASSWORD} }")
        return self.async_create_entry(title=f"Aarlo for {self._username}", data=config)

    async def _async_login_options(self) -> dict[str, Any]:
        """The options the integration itself will log in with.

        Built the same way as at runtime so the session, the cookies and
        the trusted "browser" saved here - storage_dir, user_agent and so
        on - are exactly the ones the integration picks up afterwards.
        """
        cfg = BlendedCfg(self.hass)
        await cfg.async_load_and_merge(
            {CONF_USERNAME: self._username, CONF_PASSWORD: self._password}, {}
        )
        return PyaarloCfg.create_options(self.hass, cfg.domain_config)

    async def async_step_user(self, info: dict | None = None):
        """Collect the credentials, then log in and see what 2FA the account
        needs, rather than asking the user to guess the mechanism up front.
        """

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if info is not None:
            self._username = info[CONF_USERNAME]
            self._password = info[CONF_PASSWORD]
            self._add_prefix = info.get(CONF_ADD_AARLO_PREFIX, True)

            if info.get(CONF_MANUAL_TFA) or ArloLogin is None:
                return await self.async_step_manual_tfa()

            await self._async_close_login()
            self._login = ArloLogin(**await self._async_login_options())
            step = await self._login.start()

            # Arlo already trusts this browser, or the account has no 2FA.
            # Nothing to set up; a later re-login uses the trust.
            if step == LoginStep.SUCCESS:
                return await self._async_create_login_entry({
                    CONF_TFA_TYPE: "none",
                    "tfa": "none",
                })

            if step == LoginStep.NEEDS_FACTOR:
                return await self.async_step_choose_factor()

            _LOGGER.warning(f"aarlo login failed: {self._login.last_error}")
            await self._async_close_login()
            errors["base"] = "invalid_auth"

        data_schema = {
            vol.Required(CONF_USERNAME, default=self._username): str,
            vol.Required(CONF_PASSWORD, default=self._password): str,
            vol.Required(CONF_ADD_AARLO_PREFIX, default=self._add_prefix): bool,
            vol.Optional(CONF_MANUAL_TFA, default=False): bool,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_choose_factor(self, user_input: dict[str, Any] | None = None):
        """Let the user pick one of the account's own 2FA factors."""

        errors: dict[str, str] = {}
        if self._flow_error is not None:
            errors["base"] = self._flow_error
            self._flow_error = None

        if user_input is not None:
            factor_id = user_input[CONF_FACTOR_ID]
            self._factor = next(
                (f for f in self._login.factors if f.get("factorId") == factor_id), None
            )
            step = await self._login.choose_factor(factor_id)
            if step == LoginStep.AWAITING_PUSH:
                self._push_task = None
                return await self.async_step_await_push()
            if step == LoginStep.AWAITING_CODE:
                return await self.async_step_enter_code()
            _LOGGER.warning(f"aarlo 2fa start failed: {self._login.last_error}")
            errors["base"] = "tfa_start_failed"

        return self.async_show_form(
            step_id="choose_factor",
            data_schema=vol.Schema({
                vol.Required(CONF_FACTOR_ID): _factor_selector(self._login.factors),
            }),
            errors=errors,
        )

    async def _async_wait_for_push(self) -> Any:
        step = await self._login.poll_push()
        while step == LoginStep.AWAITING_PUSH:
            await asyncio.sleep(self._login.push_poll)
            step = await self._login.poll_push()
        return step

    async def async_step_await_push(self, user_input: dict[str, Any] | None = None):
        """Wait for the user to approve the login in the Arlo app."""

        if self._push_task is None:
            self._push_task = self.hass.async_create_task(self._async_wait_for_push())

        if not self._push_task.done():
            return self.async_show_progress(
                step_id="await_push",
                progress_action="waiting_for_push",
                progress_task=self._push_task,
            )

        try:
            step = self._push_task.result()
        except Exception as e:
            _LOGGER.warning(f"aarlo push wait failed: {e}")
            step = LoginStep.FAILED
        self._push_task = None

        if step == LoginStep.SUCCESS:
            return self.async_show_progress_done(next_step_id="push_done")
        _LOGGER.warning(f"aarlo push failed: {self._login.last_error}")
        return self.async_show_progress_done(next_step_id="push_failed")

    async def async_step_push_done(self, user_input: dict[str, Any] | None = None):
        """The push was approved. Keep using that phone for later logins."""
        return await self._async_create_login_entry({
            CONF_TFA_TYPE: "push",
            CONF_TFA_SOURCE: "push",
            "tfa": "push",
            CONF_TFA_FACTOR_ID: (self._factor or {}).get("factorId"),
        })

    async def async_step_push_failed(self, user_input: dict[str, Any] | None = None):
        """Denied or not approved in time, let the user try again."""
        self._flow_error = "push_failed"
        return await self.async_step_choose_factor()

    async def async_step_enter_code(self, user_input: dict[str, Any] | None = None):
        """Collect the code Arlo sent by email or SMS."""

        errors: dict[str, str] = {}
        if user_input is not None:
            step = await self._login.submit_code(user_input[CONF_CODE])
            if step == LoginStep.SUCCESS:
                # Nothing can type a code in later, so a re-login only works
                # while Arlo trusts this browser. Say so explicitly instead of
                # leaving pyaarlo to its own default.
                factor_type = str((self._factor or {}).get("factorType", "email")).lower()
                return await self._async_create_login_entry({
                    CONF_TFA_TYPE: factor_type,
                    CONF_TFA_SOURCE: "console",
                    "tfa": f"{factor_type}:console",
                    CONF_TFA_FACTOR_ID: (self._factor or {}).get("factorId"),
                })
            if step == LoginStep.AWAITING_CODE:
                errors["base"] = "wrong_code"
            else:
                _LOGGER.warning(f"aarlo code login failed: {self._login.last_error}")
                self._flow_error = "code_failed"
                return await self.async_step_choose_factor()

        return self.async_show_form(
            step_id="enter_code",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            description_placeholders={
                "factor": _factor_label(self._factor) if self._factor else "",
            },
            errors=errors,
        )

    async def async_step_manual_tfa(self, info: dict | None = None):
        """Set up 2FA by hand instead of logging in now, e.g. to give the
        integration an IMAP mailbox it can read codes from on its own.
        """

        errors: dict[str, str] = {}
        if info is not None:
            config, errors = self._process_flow_input({**info, **self._base_config()})

            # Looks good, then create it.
            if not errors:
                _LOGGER.debug(f"aarlo-config={ {k: v for k, v in config.items() if k != CONF_PASSWORD} }")
                return self.async_create_entry(
                    title=f"Aarlo for {self._username}",
                    data=config
                )

            # Pass broken one into the GUI.
            self._tfa_username = info.get(CONF_TFA_USERNAME, "")
            self._tfa_password = info.get(CONF_TFA_PASSWORD, "")
            self._tfa_host = info.get(CONF_TFA_HOST, "")

        data_schema = {
            vol.Required(CONF_TFA_TYPE, default="IMAP"): TFA_SELECTOR,
            vol.Optional(CONF_TFA_USERNAME, default=self._tfa_username): str,
            vol.Optional(CONF_TFA_PASSWORD, default=self._tfa_password): str,
            vol.Optional(CONF_TFA_HOST, default=self._tfa_host): str,
        }

        return self.async_show_form(
            step_id="manual_tfa", data_schema=vol.Schema(data_schema), errors=errors
        )

    @callback
    def async_remove(self) -> None:
        """The flow was abandoned, drop the half finished login."""
        if self._push_task is not None and not self._push_task.done():
            self._push_task.cancel()
        if self._login is not None and getattr(self, "hass", None) is not None:
            self.hass.async_create_task(self._login.close())
        self._login = None

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
                # A pinned factor wins over the mechanism in pyaarlo, so it
                # would quietly undo the choice made here.
                new_data.pop(CONF_TFA_FACTOR_ID, None)
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

        return self.async_create_entry(
            title=f"Aarlo for {data[CONF_USERNAME]} (imported)",
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

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema({
                vol.Required("backend", default=backend_default): BACKEND_SELECTOR,
                vol.Required("http_backend", default=http_backend_default): HTTP_BACKEND_SELECTOR,
                vol.Optional("save_media_to", default=save_media_default): str,
                vol.Optional("media_retention_days", default=media_retention_default): int,
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
