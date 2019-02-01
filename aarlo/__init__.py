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

CONF_PACKET_DUMP    = 'packet_dump'
CONF_CACHE_VIDEOS   = 'cache_videos'
CONF_DB_MOTION_TIME = 'db_motion_time'
CONF_DB_DING_TIME   = 'db_ding_time'
CONF_RECENT_TIME    = 'recent_time'

SCAN_INTERVAL  = timedelta(seconds=60)
PACKET_DUMP    = False
CACHE_VIDEOS   = False
DB_MOTION_TIME = timedelta(seconds=30)
DB_DING_TIME   = timedelta(seconds=10)
RECENT_TIME    = timedelta(minutes=10)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_PACKET_DUMP, default=PACKET_DUMP): cv.boolean,
        vol.Optional(CONF_CACHE_VIDEOS, default=CACHE_VIDEOS): cv.boolean,
        vol.Optional(CONF_DB_MOTION_TIME, default=DB_MOTION_TIME): cv.time_period,
        vol.Optional(CONF_DB_DING_TIME, default=DB_DING_TIME): cv.time_period,
        vol.Optional(CONF_RECENT_TIME, default=RECENT_TIME): cv.time_period,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up an Arlo component."""
    conf = config[DOMAIN]
    username     = conf.get(CONF_USERNAME)
    password     = conf.get(CONF_PASSWORD)
    packet_dump  = conf.get(CONF_PACKET_DUMP)
    cache_videos = conf.get(CONF_CACHE_VIDEOS)
    motion_time  = conf.get(CONF_DB_MOTION_TIME).total_seconds()
    ding_time    = conf.get(CONF_DB_DING_TIME).total_seconds()
    recent_time  = conf.get(CONF_RECENT_TIME).total_seconds()

    try:
        from custom_components.aarlo.pyaarlo import PyArlo

        arlo = PyArlo( username,password,
                            dump=packet_dump,
                            db_motion_time=motion_time,db_ding_time=ding_time,
                            recent_time=recent_time )
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

