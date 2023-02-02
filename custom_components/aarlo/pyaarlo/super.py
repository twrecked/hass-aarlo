import threading
from typing import TYPE_CHECKING
from unidecode import unidecode

if TYPE_CHECKING:
    from . import PyArlo

from .constant import (
    RESOURCE_KEYS,
    RESOURCE_UPDATE_KEYS,
)


class ArloSuper(object):
    """Object class for all Arlo objects.

    Has code for:
    - attribute handling
    - event handling
    - callback/monitoring handling

    The only guaranteed pieces are:
     name: the object name
     device_id: the object id
     device_type: the object type
     unique_id: usually the device id with a GUI style prefix

    ArloLocation is the odd piece out, Arlo doesn't supply a device type
    or unique_id for this Object so we create one.
    """
    def __init__(self, name, arlo: 'PyArlo', attrs, id, type, uid=None):
        self._name = name
        self._arlo = arlo
        self._attrs = attrs
        self._id = id
        self._type = type
        self._uid = uid

        self._lock = threading.Lock()
        self._attr_cbs_ = []

        # add a listener
        self._arlo.be.add_listener(self, self._event_handler)

    def __repr__(self):
        # Representation string of object.
        return f"<{self.__class__.__name__}:{self.device_type}:{self.name}>"

    def _to_storage_key(self, attr):
        # Build a key incorporating the type!
        if isinstance(attr, list):
            return [self.__class__.__name__, self._id] + attr
        else:
            return [self.__class__.__name__, self._id, attr]

    def _event_handler(self, resource, event):
        self.vdebug(f"{self._name}: object got {resource} event")

        # Find properties. Event either contains a item called properties or it
        # is the whole thing.
        self.update_resources(event.get("properties", event))

    def _do_callbacks(self, attr, value):
        cbs = []
        with self._lock:
            for watch, cb in self._attr_cbs_:
                if watch == attr or watch == "*":
                    cbs.append(cb)
        for cb in cbs:
            cb(self, attr, value)

    def _save(self, attr, value):
        self._arlo.st.set(self._to_storage_key(attr), value, prefix=self._id)

    def _save_and_do_callbacks(self, attr, value):
        if value != self._load(attr):
            self._save(attr, value)
            self._do_callbacks(attr, value)
            self.debug(f"{attr}: NEW {str(value)[:80]}")
        else:
            self.vdebug(f"{attr}: OLD {str(value)[:80]}")

    def _load(self, attr, default=None):
        return self._arlo.st.get(self._to_storage_key(attr), default)

    def _load_matching(self, attr, default=None):
        return self._arlo.st.get_matching(self._to_storage_key(attr), default)

    @property
    def name(self):
        """Returns the device name."""
        return self._name

    @property
    def device_id(self):
        """Returns the device id."""
        return self._id

    @property
    def device_type(self):
        """Returns the device id."""
        return self._type

    @property
    def entity_id(self):
        if self._arlo.cfg.serial_ids:
            return self.device_id
        elif self._arlo.cfg.no_unicode_squash:
            return self.name.lower().replace(" ", "_")
        else:
            return unidecode(self.name.lower().replace(" ", "_"))

    @property
    def unique_id(self):
        """Returns the unique name."""
        if self._uid is None:
            self._uid = f"{self._type}-{self._id}"
        return self._uid

    def update_resources(self, props):
        for key in RESOURCE_KEYS + RESOURCE_UPDATE_KEYS:
            value = props.get(key, None)
            if value is not None:
                self._save_and_do_callbacks(key, value)

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

    def debug(self, msg):
        self._arlo.debug(f"{self._name}: {msg}")

    def vdebug(self, msg):
        self._arlo.vdebug(f"{self._name}: {msg}")
