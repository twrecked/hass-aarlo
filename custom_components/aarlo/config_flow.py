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

    async def async_step_user(self, user_input: dict = None):
        """Handle user initiated flow."""
        user_input = user_input or {}
        errors = {}

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