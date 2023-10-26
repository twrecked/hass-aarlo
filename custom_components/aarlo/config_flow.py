"""Config flow for Aarlo"""

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
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


class AarloFlowHandler(ConfigFlow, domain=DOMAIN):
    """Aarlo config flow."""

    VERSION = 1

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
        domain_config = UpgradeCfg.create_flow_config(import_data)

        return self.async_create_entry(
            title=f"{DEFAULT_IMPORTED_NAME} {DOMAIN}", data={
                "naming_style": "original",
                "imported": True,
                DOMAIN: domain_config
            })
