"""
Support for Arlo Cameras and Accesories.

For more details about this platform, please refer to the documentation at
https://github.com/twrecked/hass-aarlo/blob/master/README.md
"""

import asyncio
import json
import logging
import pprint
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE,
    CONF_USERNAME,
    Platform
)
from homeassistant.core import (
    DOMAIN as HOMEASSISTANT_DOMAIN,
    HomeAssistant,
    callback
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.issue_registry import (
    async_create_issue,
    IssueSeverity
)
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.device_registry as dr

from pyaarlo.constant import (
    DEFAULT_AUTH_HOST,
    DEFAULT_HOST,
    DEVICE_ID_KEY,
    DEVICE_NAME_KEY,
    SIREN_STATE_KEY,
    MQTT_HOST
)

from .const import *
from .utils import get_entity_from_domain
from .cfg import BlendedCfg, PyaarloCfg


__version__ = "0.9.0-alpha.4"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        COMPONENT_DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOST): cv.url,
                vol.Optional(CONF_AUTH_HOST): cv.url,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
                vol.Optional(CONF_PACKET_DUMP, default=PACKET_DUMP): cv.boolean,
                vol.Optional(CONF_CACHE_VIDEOS, default=CACHE_VIDEOS): cv.boolean,
                vol.Optional(
                    CONF_DB_MOTION_TIME, default=DB_MOTION_TIME
                ): cv.time_period,
                vol.Optional(CONF_DB_DING_TIME, default=DB_DING_TIME): cv.time_period,
                vol.Optional(CONF_RECENT_TIME, default=RECENT_TIME): cv.time_period,
                vol.Optional(CONF_LAST_FORMAT, default=LAST_FORMAT): cv.string,
                vol.Optional(CONF_CONF_DIR, default=CONF_DIR): cv.string,
                vol.Optional(CONF_REQ_TIMEOUT, default=REQ_TIMEOUT): cv.time_period,
                vol.Optional(CONF_STR_TIMEOUT, default=STR_TIMEOUT): cv.time_period,
                vol.Optional(CONF_NO_MEDIA_UP, default=NO_MEDIA_UP): cv.boolean,
                vol.Optional(CONF_MEDIA_RETRY, default=MEDIA_RETRY): vol.All(
                    cv.ensure_list, [cv.positive_int]
                ),
                vol.Optional(CONF_SNAPSHOT_CHECKS, default=list()): vol.All(
                    cv.ensure_list, [cv.positive_int]
                ),
                vol.Optional(CONF_USER_AGENT, default=USER_AGENT): cv.string,
                vol.Optional(CONF_MODE_API, default=MODE_API): cv.string,
                vol.Optional(
                    CONF_DEVICE_REFRESH, default=DEVICE_REFRESH
                ): cv.positive_int,
                vol.Optional(CONF_MODE_REFRESH, default=MODE_REFRESH): cv.positive_int,
                vol.Optional(
                    CONF_RECONNECT_EVERY, default=RECONNECT_EVERY
                ): cv.positive_int,
                vol.Optional(CONF_VERBOSE_DEBUG, default=VERBOSE_DEBUG): cv.boolean,
                vol.Optional(
                    CONF_INJECTION_SERVICE, default=DEFAULT_INJECTION_SERVICE
                ): cv.boolean,
                vol.Optional(
                    CONF_SNAPSHOT_TIMEOUT, default=SNAPSHOT_TIMEOUT
                ): cv.time_period,
                vol.Optional(CONF_TFA_SOURCE, default=DEFAULT_TFA_SOURCE): cv.string,
                vol.Optional(CONF_TFA_TYPE, default=DEFAULT_TFA_TYPE): cv.string,
                vol.Optional(CONF_TFA_HOST, default=DEFAULT_TFA_HOST): cv.string,
                vol.Optional(
                    CONF_TFA_USERNAME, default=DEFAULT_TFA_USERNAME
                ): cv.string,
                vol.Optional(
                    CONF_TFA_PASSWORD, default=DEFAULT_TFA_PASSWORD
                ): cv.string,
                vol.Optional(CONF_TFA_TIMEOUT, default=DEFAULT_TFA_TIMEOUT): cv.time_period,
                vol.Optional(CONF_TFA_TOTAL_TIMEOUT, default=DEFAULT_TFA_TOTAL_TIMEOUT): cv.time_period,
                vol.Optional(
                    CONF_LIBRARY_DAYS, default=DEFAULT_LIBRARY_DAYS
                ): cv.positive_int,
                vol.Optional(CONF_SERIAL_IDS, default=SERIAL_IDS): cv.boolean,
                vol.Optional(CONF_STREAM_SNAPSHOT, default=STREAM_SNAPSHOT): cv.boolean,
                vol.Optional(
                    CONF_STREAM_SNAPSHOT_STOP, default=STREAM_SNAPSHOT_STOP
                ): cv.positive_int,
                vol.Optional(CONF_SAVE_UPDATES_TO, default=SAVE_UPDATES_TO): cv.string,
                vol.Optional(
                    CONF_USER_STREAM_DELAY, default=USER_STREAM_DELAY
                ): cv.positive_int,
                vol.Optional(CONF_SAVE_MEDIA_TO, default=SAVE_MEDIA_TO): cv.string,
                vol.Optional(
                    CONF_NO_UNICODE_SQUASH, default=NO_UNICODE_SQUASH
                ): cv.boolean,
                vol.Optional(CONF_SAVE_SESSION, default=SAVE_SESSION): cv.boolean,
                vol.Optional(CONF_BACKEND, default=DEFAULT_BACKEND): cv.string,
                vol.Optional(CONF_CIPHER_LIST, default=DEFAULT_CIPHER_LIST): cv.string,
                vol.Optional(CONF_MQTT_HOST): cv.string,
                vol.Optional(CONF_MQTT_HOSTNAME_CHECK, default=DEFAULT_MQTT_HOSTNAME_CHECK): cv.boolean,
                vol.Optional(CONF_MQTT_TRANSPORT): cv.string,

                # deprecated
                vol.Optional(CONF_HIDE_DEPRECATED_SERVICES, default=True): cv.boolean,
                vol.Optional(CONF_HTTP_CONNECTIONS, default=5): cv.positive_int,
                vol.Optional(CONF_HTTP_MAX_SIZE, default=10): cv.positive_int,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_VOLUME = "volume"
ATTR_DURATION = "duration"

SERVICE_SIREN_ON = "siren_on"
SERVICE_SIRENS_ON = "sirens_on"
SERVICE_SIREN_OFF = "siren_off"
SERVICE_SIRENS_OFF = "sirens_off"
SERVICE_RESTART = "restart_device"
SERVICE_INJECT_RESPONSE = "inject_response"
SIREN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_DURATION): cv.positive_int,
    vol.Required(ATTR_VOLUME): cv.positive_int,
})
SIRENS_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_DURATION): cv.positive_int,
    vol.Required(ATTR_VOLUME): cv.positive_int,
})
SIREN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
})
SIRENS_OFF_SCHEMA = vol.Schema({
})
INJECT_RESPONSE_SCHEMA = vol.Schema({
    vol.Required("filename"): cv.string,
})
RESTART_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
})

ARLO_PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.SIREN,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up an momentary component.
    """

    hass.data.setdefault(COMPONENT_DOMAIN, {})

    # See if we have already imported the data. If we haven't then do it now.
    config_entry = _async_find_aarlo_config(hass)
    if not config_entry:
        _LOGGER.debug('importing a YAML setup')
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                COMPONENT_DOMAIN,
                context={CONF_SOURCE: SOURCE_IMPORT},
                data=config
            )
        )

        async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{COMPONENT_DOMAIN}",
            is_fixable=False,
            issue_domain=COMPONENT_DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": COMPONENT_DOMAIN,
                "integration_title": "Aarlo Cameras",
            },
        )

        return True

    _LOGGER.debug('ignoring a YAML setup')
    return True


@callback
def _async_find_aarlo_config(hass):
    """ If we have anything in config_entries for aarlo we consider it
    configured and will ignore the YAML.
    """
    for entry in hass.config_entries.async_entries(COMPONENT_DOMAIN):
        return entry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug(f'async setup for aarlo')

    # Get the blended config.
    cfg = BlendedCfg(hass)
    await cfg.async_load_and_merge(entry.data, entry.options)
    domain_config = cfg.domain_config
    injection_service = domain_config.get(CONF_INJECTION_SERVICE, False)

    # Seed entry.options from aarlo.yaml if missing
    if any(k not in entry.options for k in ("backend", "http_backend", "save_media_to")):
        new_options = dict(entry.options)
        updated = False
        for k in ("backend", "http_backend", "save_media_to"):
            if k not in new_options and k in domain_config:
                new_options[k] = domain_config[k]
                updated = True
        if updated and hasattr(hass.config_entries, "async_update_entry"):
            hass.config_entries.async_update_entry(entry, options=new_options)

    # Try to login to aarlo.
    arlo = await async_login(hass, domain_config)
    if arlo is None:
        return False

    # We've logged in so create the session config.
    hass.data[COMPONENT_DATA] = arlo
    hass.data[COMPONENT_SERVICES] = {}
    hass.data[COMPONENT_CONFIG] = {
        COMPONENT_DOMAIN: domain_config,
        str(Platform.ALARM_CONTROL_PANEL): cfg.alarm_config,
        str(Platform.BINARY_SENSOR): cfg.binary_sensor_config,
        str(Platform.SENSOR): cfg.sensor_config,
        str(Platform.SWITCH): cfg.switch_config,
    }
    _LOGGER.debug(f"update hass data {hass.data[COMPONENT_CONFIG]}")
    
    # Create a pseudo device. We use this for device less entities.
    aarlo_device = {
        DEVICE_NAME_KEY: arlo.name,
        DEVICE_ID_KEY: arlo.device_id,
        "modelId": arlo.model_id
    }
    await _async_get_or_create_momentary_device_in_registry(hass, entry, aarlo_device)

    # create the real devices
    for device in arlo.devices:
        _LOGGER.debug(f"would try to add {device[DEVICE_NAME_KEY]}")
        await _async_get_or_create_momentary_device_in_registry(hass, entry, device)

    # Create the entities.
    await hass.config_entries.async_forward_entry_setups(entry, ARLO_PLATFORMS)

    # Make sure we pick up config changes.
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Component services
    has_sirens = False
    for device in arlo.cameras + arlo.base_stations:
        if device.has_capability(SIREN_STATE_KEY):
            has_sirens = True

    async def async_service_callback(call):
        """Call aarlo service handler."""
        _LOGGER.info("%s service called", call.service)
        if has_sirens:
            if call.service == SERVICE_SIREN_ON:
                await aarlo_siren_on(hass, call)
            elif call.service == SERVICE_SIRENS_ON:
                await aarlo_sirens_on(hass, call)
            elif call.service == SERVICE_SIREN_OFF:
                await aarlo_siren_off(hass, call)
            elif call.service == SERVICE_SIRENS_OFF:
                await aarlo_sirens_off(hass, call)
        if call.service == SERVICE_RESTART:
            await aarlo_restart_device(hass, call)
        if call.service == SERVICE_INJECT_RESPONSE:
            await aarlo_inject_response(hass, call)

    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_SIREN_ON,
        async_service_callback,
        schema=SIREN_ON_SCHEMA,
    )
    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_SIRENS_ON,
        async_service_callback,
        schema=SIRENS_ON_SCHEMA,
    )
    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_SIREN_OFF,
        async_service_callback,
        schema=SIREN_OFF_SCHEMA,
    )
    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_SIRENS_OFF,
        async_service_callback,
        schema=SIRENS_OFF_SCHEMA,
    )
    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_RESTART,
        async_service_callback,
        schema=RESTART_SCHEMA,
    )
    if injection_service:
        hass.services.async_register(
            COMPONENT_DOMAIN,
            SERVICE_INJECT_RESPONSE,
            async_service_callback,
            schema=INJECT_RESPONSE_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"unloading it {entry.title}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ARLO_PLATFORMS)
    if unload_ok:
        arlo = hass.data.get(COMPONENT_DATA)
        if arlo is not None:
            await arlo.stop(logout=True)
        hass.data.pop(COMPONENT_DATA, None)
        hass.data.pop(COMPONENT_SERVICES, None)
        hass.data.pop(COMPONENT_CONFIG, None)
    _LOGGER.debug(f"ok={unload_ok}")

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ARLO_PLATFORMS)
    if not unload_ok:
        _LOGGER.warning(f"failed to reconfigure Aarlo {entry.title}")
        return

    _LOGGER.debug("reconfiguring...")
    cfg = BlendedCfg(hass)
    await cfg.async_load_and_merge(entry.data, entry.options)
    hass.data[COMPONENT_CONFIG] = {
        COMPONENT_DOMAIN: cfg.domain_config,
        str(Platform.ALARM_CONTROL_PANEL): cfg.alarm_config,
        str(Platform.BINARY_SENSOR): cfg.binary_sensor_config,
        str(Platform.SENSOR): cfg.sensor_config,
        str(Platform.SWITCH): cfg.switch_config,
    }
    # XXX remove orphaned entries
    await hass.config_entries.async_forward_entry_setups(entry, ARLO_PLATFORMS)


async def _async_get_or_create_momentary_device_in_registry(
        hass: HomeAssistant, entry: ConfigEntry, device
) -> None:
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(COMPONENT_DOMAIN, device[DEVICE_ID_KEY])},
        manufacturer=COMPONENT_BRAND,
        name=device[DEVICE_NAME_KEY],
        model=device['modelId'],
        sw_version=__version__
    )


async def async_login(hass: HomeAssistant, conf: dict):
    sleep = 15
    attempt = 1
    while True:
        try:
            from pyaarlo import PyArlo

            if attempt != 1:
                _LOGGER.debug("login-attempt=%s", attempt)

            options = PyaarloCfg.create_options(hass, conf)
            arlo = await PyArlo.create(**options)
            if arlo.is_connected:
                _LOGGER.debug("login succeeded, attempt=%s", attempt)
                return arlo
            await arlo.stop()

            if attempt == 1:
                persistent_notification.async_create(
                    hass=hass,
                    message=(
                        f"Error: {arlo.last_error}<br />"
                        "If error persists you might need to change config and restart."
                    ),
                    title=NOTIFICATION_TITLE,
                    notification_id=NOTIFICATION_ID,
                )
            _LOGGER.error(
                "unable to connect to Arlo: attempt=%s,sleep=%s,error=%s",
                attempt,
                sleep,
                arlo.last_error,
            )

        except Exception as ex:
            if attempt == 1:
                persistent_notification.async_create(
                    hass=hass,
                    message=(
                        f"Error: {ex}<br />"
                        "If error persists you might need to change config and restart."
                    ),
                    title=NOTIFICATION_TITLE,
                    notification_id=NOTIFICATION_ID,
                )
            _LOGGER.error(
                "unable to connect to Arlo: attempt=%s,sleep=%s,error=%s",
                attempt,
                sleep,
                str(ex),
            )

        # line up a retry
        attempt = attempt + 1
        if attempt == 5:
            _LOGGER.error("unable to connect to Arlo: stopping retries, too many failures")
            return None
        await asyncio.sleep(sleep)
        sleep = min(300, sleep * 2)


login = async_login


async def aarlo_siren_on(hass: HomeAssistant, call) -> None:
    for entity_id in call.data["entity_id"]:
        try:
            volume = call.data["volume"]
            duration = call.data["duration"]
            device = get_entity_from_domain(
                hass, [ALARM_DOMAIN, CAMERA_DOMAIN], entity_id
            )
            if hasattr(device, "async_siren_on"):
                await device.async_siren_on(duration=duration, volume=volume)
            else:
                res = device.siren_on(duration=duration, volume=volume)
                if asyncio.iscoroutine(res):
                    await res
            _LOGGER.info("%s siren on %s/%s", entity_id, volume, duration)
        except HomeAssistantError:
            _LOGGER.info("%s siren device not found", entity_id)


async def aarlo_sirens_on(hass: HomeAssistant, call) -> None:
    arlo = hass.data[COMPONENT_DATA]
    volume = call.data["volume"]
    duration = call.data["duration"]
    tasks = []
    for device in arlo.cameras + arlo.base_stations:
        if device.has_capability(SIREN_STATE_KEY):
            _LOGGER.info("%s siren on %s/%s", device.unique_id, volume, duration)
            res = device.siren_on(duration=duration, volume=volume)
            if asyncio.iscoroutine(res):
                tasks.append(res)
    if tasks:
        await asyncio.gather(*tasks)


async def aarlo_siren_off(hass: HomeAssistant, call) -> None:
    for entity_id in call.data["entity_id"]:
        try:
            device = get_entity_from_domain(
                hass, [ALARM_DOMAIN, CAMERA_DOMAIN], entity_id
            )
            if hasattr(device, "async_siren_off"):
                await device.async_siren_off()
            else:
                res = device.siren_off()
                if asyncio.iscoroutine(res):
                    await res
            _LOGGER.info("%s siren off", entity_id)
        except HomeAssistantError:
            _LOGGER.info("%s siren not found", entity_id)


async def aarlo_sirens_off(hass: HomeAssistant, _call) -> None:
    arlo = hass.data[COMPONENT_DATA]
    tasks = []
    for device in arlo.cameras + arlo.base_stations:
        if device.has_capability(SIREN_STATE_KEY):
            _LOGGER.info("%s siren off", device.unique_id)
            res = device.siren_off()
            if asyncio.iscoroutine(res):
                tasks.append(res)
    if tasks:
        await asyncio.gather(*tasks)


async def aarlo_restart_device(hass: HomeAssistant, call) -> None:
    for entity_id in call.data["entity_id"]:
        try:
            device = get_entity_from_domain(
                hass, [ALARM_DOMAIN, CAMERA_DOMAIN], entity_id
            )
            if hasattr(device, "async_restart"):
                await device.async_restart()
            elif hasattr(device, "restart"):
                res = device.restart()
                if asyncio.iscoroutine(res):
                    await res
            _LOGGER.info("%s restarted", entity_id)
        except HomeAssistantError:
            _LOGGER.info("%s device not found", entity_id)


async def aarlo_inject_response(hass: HomeAssistant, call) -> None:
    patch_file = hass.config.path(call.data["filename"])
    if not hass.config.is_allowed_path(patch_file):
        _LOGGER.error("Can't read %s, no access to path!", patch_file)
        return
    try:
        def _read_json():
            with open(patch_file, "r", encoding="utf-8") as file:
                return json.load(file)
        packet = await hass.async_add_executor_job(_read_json)
        if packet is not None:
            _LOGGER.debug("injecting->%s", pprint.pformat(packet))
            res = hass.data[COMPONENT_DATA].inject_response(packet)
            if asyncio.iscoroutine(res):
                await res
    except Exception as ex:
        _LOGGER.error("inject response failed: %s", ex)
