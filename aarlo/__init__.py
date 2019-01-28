"""
This component provides support for Netgear Arlo IP cameras.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/arlo/
"""
import logging
from datetime import timedelta
import voluptuous as vol
from requests.exceptions import HTTPError, ConnectTimeout

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.dispatcher import dispatcher_send

from homeassistant.const import (
        CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL)

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Data provided by arlo.netgear.com"
DATA_ARLO = 'data_aarlo'
DEFAULT_BRAND = 'Netgear Arlo'
DOMAIN = 'aarlo'

NOTIFICATION_ID = 'aarlo_notification'
NOTIFICATION_TITLE = 'aarlo Component Setup'

SCAN_INTERVAL = timedelta(seconds=60)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up an Arlo component."""
    conf = config[DOMAIN]
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    try:
        from custom_components.aarlo.pyaarlo import PyArlo

        arlo = PyArlo( username,password )
        if not arlo.is_connected:
            return False

        hass.data[DATA_ARLO] = arlo

    except (ConnectTimeout, HTTPError) as ex:
        _LOGGER.error("Unable to connect to Netgear Arlo: %s", str(ex))
        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    return True

