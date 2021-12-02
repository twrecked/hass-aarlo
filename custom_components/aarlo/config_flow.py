"""Config flow for Aarlo"""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)
from .const import (
    DOMAIN,
    CONF_TFA_USERNAME,
    CONF_TFA_PASSWORD,
    CONF_TFA_HOST
)


class AarloFlowHandler(ConfigFlow, domain=DOMAIN):
    """Aarlo config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.email = None
        self.password = None
        self.tfaUsername = None
        self.tfaPassword = None
        self.tfaHost = None

    async def async_step_user(self, info: dict = None):
        """Handle user initiated flow."""
        errors = {}

        if info is not None:
            # TODO need to add error handling for blank fields / bad data
            # process the information
            if not self.email or not self.password or not self.tfaUsername or not self.tfaPassword or not self.tfaHost:
                errors["base"] = "missing_field"
            else:
                return self.async_create_entry(title=f"Arlo - ${self.email}", data=info)

        data_schema = {
            vol.Required(CONF_USERNAME, default=self.email): str,
            vol.Required(CONF_PASSWORD, default=self.password): str,
            vol.Required(CONF_TFA_USERNAME, default=self.tfaUsername): str,
            vol.Required(CONF_TFA_PASSWORD, default=self.tfaPassword): str,
            vol.Required(CONF_TFA_HOST, default=self.tfaHost): str,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )
