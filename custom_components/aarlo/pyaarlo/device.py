from typing import TYPE_CHECKING

from unidecode import unidecode

if TYPE_CHECKING:
    from . import PyArlo

from .constant import (
    BATTERY_KEY,
    BATTERY_TECH_KEY,
    CHARGER_KEY,
    CHARGING_KEY,
    CONNECTION_KEY,
    CONNECTIVITY_KEY,
    DEVICE_KEYS,
    RESOURCE_KEYS,
    RESOURCE_UPDATE_KEYS,
    SIGNAL_STR_KEY,
    TIMEZONE_KEY,
    XCLOUD_ID_KEY,
)
from .super import ArloSuper


class ArloDevice(ArloSuper):
    """Base class for all Arlo devices.

    Has code to handle providing common attributes and comment event handling.
    """

    def __init__(self, name, arlo: 'PyArlo', attrs):
        super().__init__(name, arlo, attrs,
                         id=attrs.get("deviceId", "unknown"),
                         type=attrs.get("deviceType", "unknown"),
                         uid=attrs.get("uniqueId", None))

        # We save this here but only expose it directly in the ArloChild class.
        # Some devices are their own parents and we need to know that at the ArloDevice
        # or ArloChild class so we leave this here as a short cut.
        self._parent_id = attrs.get("parentId", None)

        # Activities. Used by camera for now but made available to all.
        self._activities = {}

        # Build initial values. These can be at the top level or in the
        # properties dictionary.
        for key in DEVICE_KEYS:
            value = attrs.get(key, None)
            if value is not None:
                self._save(key, value)
        props = attrs.get("properties", {})
        for key in RESOURCE_KEYS + RESOURCE_UPDATE_KEYS:
            value = props.get(key, None)
            if value is not None:
                self._save(key, value)

    @property
    def entity_id(self):
        if self._arlo.cfg.serial_ids:
            return self.device_id
        elif self._arlo.cfg.no_unicode_squash:
            return self.name.lower().replace(" ", "_")
        else:
            return unidecode(self.name.lower().replace(" ", "_"))

    @property
    def resource_id(self):
        """Returns the resource id, used for making requests and checking responses.

        For base stations has the format [DEVICE-ID] and for other devices has
        the format [RESOURCE-TYPE]/[DEVICE-ID]
        """
        return self.device_id

    @property
    def resource_type(self):
        """Returns the type of resource this is.

        For now it's, `cameras`, `doorbells`, `lights` or `basestations`.
        """
        return None

    @property
    def serial_number(self):
        """Returns the device serial number."""
        return self.device_id

    @property
    def model_id(self):
        """Returns the model id."""
        return self._attrs.get("modelId", None)

    @property
    def hw_version(self):
        """Returns the hardware version."""
        return self._attrs.get("properties", {}).get("hwVersion", None)

    @property
    def timezone(self):
        """Returns the timezone."""
        time_zone = self._load(TIMEZONE_KEY, None)
        if time_zone is None:
            return self._attrs.get("properties", {}).get("olsonTimeZone", None)
        return time_zone

    @property
    def user_id(self):
        """Returns the user id."""
        return self._attrs.get("userId", None)

    @property
    def user_role(self):
        """Returns the user role."""
        return self._attrs.get("userRole", None)

    @property
    def xcloud_id(self):
        """Returns the device's xcloud id."""
        return self._load(XCLOUD_ID_KEY, "UNKNOWN")

    @property
    def web_id(self):
        """Return the device's web id."""
        return self.user_id + "_web"

    @property
    def is_own_parent(self):
        """Returns True if device is its own parent.

        Can work from child or parent class.
        """
        return self._parent_id == self.device_id

    def attribute(self, attr, default=None):
        """Return the value of attribute attr.

        PyArlo stores its state in key/value pairs. This returns the value associated with the key.

        See PyArlo for a non-exhaustive list of attributes.

        :param attr: Attribute to look up.
        :type attr: str
        :param default: value to return if not found.
        :return: The value associated with attribute or `default` if not found.
        """
        value = self._load(attr, None)
        if value is None:
            value = self._attrs.get(attr, None)
        if value is None:
            value = self._attrs.get("properties", {}).get(attr, None)
        if value is None:
            value = default
        return value

    def add_attr_callback(self, attr, cb):
        """Add an callback to be triggered when an attribute changes.

        Used to register callbacks to track device activity. For example, get a notification whenever
        motion stop and starts.

        See PyArlo for a non-exhaustive list of attributes.

        :param attr: Attribute - eg `motionStarted` - to monitor.
        :type attr: str
        :param cb: Callback to run.
        """
        with self._lock:
            self._attr_cbs_.append((attr, cb))

    def has_capability(self, cap):
        """Is the device capable of performing activity cap:.

        Used to determine if devices can perform certain actions, like motion or audio detection.

        See attribute list against PyArlo.

        :param cap: Attribute - eg `motionStarted` - to check.
        :return: `True` it is, `False` it isn't.
        """
        if cap in (CONNECTION_KEY,):
            return True
        return False

    @property
    def state(self):
        """Returns a string describing the device's current state."""
        return "idle"

    @property
    def is_on(self):
        """Returns `True` if the device is on, `False` otherwise."""
        return True

    def turn_on(self):
        """Turn the device on."""
        pass

    def turn_off(self):
        """Turn the device off."""
        pass

    @property
    def is_unavailable(self):
        """Returns `True` if the device is unavailable, `False` otherwise.

        **Note:** Sorry about the double negative.
        """
        return self._load(CONNECTION_KEY, "unknown") == "unavailable"

    @property
    def battery_level(self):
        """Returns the current battery level."""
        return self._load(BATTERY_KEY, 100)

    @property
    def battery_tech(self):
        """Returns the current battery technology.

        Is it rechargable, wired...
        """
        return self._load(BATTERY_TECH_KEY, "None")

    @property
    def has_batteries(self):
        """Returns `True` if device has batteries installed, `False` otherwise."""
        return self.battery_tech != "None"

    @property
    def charger_type(self):
        """Returns how the device is recharging."""
        return self._load(CHARGER_KEY, "None")

    @property
    def has_charger(self):
        """Returns `True` if the charger is plugged in, `False` otherwise."""
        return self.charger_type != "None"

    @property
    def is_charging(self):
        """Returns `True` if the device is charging, `False` otherwise."""
        return self._load(CHARGING_KEY, "off").lower() == "on"

    @property
    def is_charger_only(self):
        """Returns `True` if the cahrger is plugged in with no batteries, `False` otherwise."""
        return self.battery_tech == "None" and self.has_charger

    @property
    def is_corded(self):
        """Returns `True` if the device is connected directly to a power outlet, `False` otherwise.

        The device can't have any battery option, it can't be using a charger, it has to run
        directly from a plug. ie, an original base station.
        """
        return not self.has_batteries and not self.has_charger

    @property
    def using_wifi(self):
        """Returns `True` if the device is connected to the wifi, `False` otherwise.

        This means connecting directly to your home wifi, not connecting to and Arlo basestation.
        """
        return self._attrs.get(CONNECTIVITY_KEY, {}).get("type", "").lower() == "wifi"

    @property
    def signal_strength(self):
        """Returns the WiFi signal strength (0-5)."""
        return self._load(SIGNAL_STR_KEY, 3)


class ArloChildDevice(ArloDevice):
    """Base class for all Arlo devices that attach to a base station."""

    def __init__(self, name, arlo, attrs):
        super().__init__(name, arlo, attrs)

        self._arlo.debug("parent is {}".format(self._parent_id))
        self._arlo.vdebug("resource is {}".format(self.resource_id))

    def _event_handler(self, resource, event):
        self._arlo.vdebug("{}: child got {} event **".format(self.name, resource))

        if resource.endswith("/states"):
            self._arlo.bg.run(self.base_station.update_mode)
            return

        # Pass event to lower level.
        super()._event_handler(resource, event)

    @property
    def resource_type(self):
        """Return the resource type this child device describes.

        Currently limited to `camera`, `doorbell` and `light`.
        """
        return "child"

    @property
    def resource_id(self):
        """Returns the child device resource id.

        Some devices - certain cameras - can provide other types.
        """
        return self.resource_type + "/" + self.device_id

    @property
    def parent_id(self):
        """Returns the parent device id.

        **Note:** Some devices - ArloBaby for example - are their own parents.
        """
        if self._parent_id is not None:
            return self._parent_id
        return self.device_id

    @property
    def timezone(self):
        """Returns the timezone.

        Tries to be clever. If it doesn't have a timezone it will try its
        basestation.
        """
        time_zone = super().timezone
        if time_zone is None:
            return self.base_station.timezone
        return time_zone

    @property
    def base_station(self):
        """Returns the base station controlling this device.

        Some devices - ArloBaby for example - are their own parents. If we
        can't find a basestation, this returns the first one (if any exist).
        """
        # look for real parents
        for base in self._arlo.base_stations:
            if base.device_id == self.parent_id:
                return base

        # some cameras don't have base stations... it's its own base station...
        for base in self._arlo.base_stations:
            if base.device_id == self.device_id:
                return base

        # no idea!
        if len(self._arlo.base_stations) > 0:
            return self._arlo.base_stations[0]

        self._arlo.error("Could not find any base stations for device " + self._name)
        return None

    @property
    def is_unavailable(self):
        if not self.base_station:
            return True

        return (
            self.base_station.is_unavailable
            or self._load(CONNECTION_KEY, "unknown") == "unavailable"
        )

    @property
    def too_cold(self):
        """Returns `True` if the device too cold to operate, `False` otherwise."""
        return self._load(CONNECTION_KEY, "unknown") == "thermalShutdownCold"

    @property
    def state(self):
        if self.is_unavailable:
            return "unavailable"
        if not self.is_on:
            return "off"
        if self.too_cold:
            return "offline, too cold"
        return "idle"
