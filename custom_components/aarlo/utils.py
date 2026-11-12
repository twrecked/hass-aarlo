from typing import Any
from homeassistant.util import slugify
from .const import (
    CONF_ADD_AARLO_PREFIX,
    CONF_DEVICE_FIRST_NAMING,
    DEFAULT_DEVICE_FIRST_NAMING,
)


def get_entity_identifiers(
    aarlo_config: dict[str, Any],
    device: Any,
    function_name: str | None = None,
) -> tuple[str, str]:
    """Calculate (unique_id, suggested_object_id) for an entity.

    :param aarlo_config: integration configuration dictionary
    :param device: the PyArlo device (camera, light, doorbell, base station, etc.)
    :param function_name: functional suffix (e.g. "battery_level", "motion", "spotlight", "siren", "snapshot")
    :return: (unique_id, suggested_object_id)
    """
    prefix = "aarlo_" if aarlo_config.get(CONF_ADD_AARLO_PREFIX, True) else ""
    device_first = aarlo_config.get(CONF_DEVICE_FIRST_NAMING, DEFAULT_DEVICE_FIRST_NAMING)

    dev_name = device.name if isinstance(getattr(device, "name", None), str) else str(getattr(device, "device_id", "device"))
    dev_slug = slugify(dev_name)
    dev_entity_id = slugify(str(getattr(device, "entity_id", dev_slug)))

    # 1. Primary device entities (camera, standalone light, alarm panel, media player)
    if function_name is None:
        unique_id = dev_entity_id
        suggested_object_id = f"{prefix}{dev_slug}"
        return unique_id, suggested_object_id

    # 2. Functional child entities
    fn_slug = slugify(function_name)

    if device_first:
        unique_id = f"{dev_entity_id}_{fn_slug}"
        suggested_object_id = f"{prefix}{dev_slug}_{fn_slug}"
    else:
        unique_id = f"{fn_slug}_{dev_entity_id}"
        suggested_object_id = f"{prefix}{fn_slug}_{dev_slug}"

    return unique_id, suggested_object_id

import logging
from traceback import extract_stack

from homeassistant.exceptions import HomeAssistantError


_LOGGER = logging.getLogger(__name__)


def is_homekit():
    for frame in reversed(extract_stack()):
        try:
            frame.filename.index("homeassistant/components/homekit")
            _LOGGER.debug("homekit detected")
            return True
        except ValueError:
            continue
    _LOGGER.debug("not homekit detected")
    return False


def get_entity_from_domain(hass, domains, entity_id):
    domains = domains if isinstance(domains, list) else [domains]
    for domain in domains:
        component = hass.data.get(domain)
        if component is None:
            raise HomeAssistantError("{} component not set up".format(domain))
        entity = component.get_entity(entity_id)
        if entity is not None:
            return entity
    raise HomeAssistantError("{} not found in {}".format(entity_id, ",".join(domains)))


def to_bool(value) -> bool:
    """Try our hardest to make a bool.
    """
    if isinstance(value, str):
        value = value.lower()
        if value == "off" or value == "no":
            return False
        return True
    return bool(value)
