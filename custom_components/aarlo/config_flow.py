"""Config flow for Aarlo"""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from .const import DOMAIN


class AarloFlowHandler(ConfigFlow, domain=DOMAIN):
    """Aarlo config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.email = None
        self.password = None
        self.shouldProcess = False

    async def async_step_user(self, info: dict = None):
        """Handle user initiated flow."""
        user_input = info or {}
        errors = {}

        if user_input is not None:
            # process the information
            self.shouldProcess = True

        data_schema = {
            vol.Required("Username"): str,
            vol.Required("Password"): str,
            vol.Required("TFA Username"): str,
            vol.Required("TFA Password"): str,
            vol.Required("TFA HOST"): str,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )
