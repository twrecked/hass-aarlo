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
