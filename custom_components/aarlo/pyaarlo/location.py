import pprint
import time
import threading

from .constant import (
    DEFAULT_MODES,
    DEFINITIONS_PATH,
    MODE_ID_TO_NAME_KEY,
    MODE_IS_SCHEDULE_KEY,
    MODE_KEY,
    MODE_NAME_TO_ID_KEY,
    MODE_UPDATE_INTERVAL,
    TIMEZONE_KEY,
    LOCATION_MODES_PATH_FORMAT,
    LOCATION_ACTIVEMODE_PATH_FORMAT,
    MODE_REVISION_KEY
)
from .util import time_to_arlotime

# Represnts a Location object; each Arlo account can have multiple owned locations and
# multiple shared locations.
#
# Should there be a new base class for this as well as ArloDevice?
class ArloLocation():
    def __init__(self, arlo, attrs):
        # add a listener
        self._name = attrs.get("locationId")
        self._gatewayDeviceUniqueIds = attrs.get("gatewayDeviceIds")
        self._location_id = self._name
        self._arlo = arlo
        self._attrs = attrs
        
        # BE only knows how to listen for device events.
        #self._arlo.be.add_listener(self, self._event_handler)

        self._lock = threading.Lock()
        self._attr_cbs_ = []

        self._last_update = 0

    def _id_to_name(self, mode_id):
        return self._load([MODE_ID_TO_NAME_KEY, mode_id], None)

    def _name_to_id(self, mode_name):
        return self._load([MODE_NAME_TO_ID_KEY, mode_name.lower()], None)

    def _parse_modes(self, modes):
        for mode in modes.items():
            mode_id = mode[0]
            mode_name = mode[1].get("name", "")
            if mode_id and mode_name != "":
                self._arlo.error(mode_id + "<=M=>" + mode_name)
                self._save([MODE_ID_TO_NAME_KEY, mode_id], mode_name)
                self._save([MODE_NAME_TO_ID_KEY, mode_name.lower()], mode_id)

    def _set_mode(self, event):
        
        #TODO
        if mode_ids:
            self._arlo.debug(self.name + " mode change " + mode_ids[0])
            mode_name = self._id_to_name(mode_ids[0])
            self._save_and_do_callbacks(MODE_KEY, mode_name)

    def _event_handler(self, resource, event):
        self._arlo.debug(self.name + " BASE got " + resource)

        # modes on base station
        if resource == "modes":
            props = event.get("properties", {})

            # list of modes - recheck?
            self._parse_modes(props.get("modes", []))

            # mode change?
            if "activeMode" in props:
                self._save_and_do_callbacks(
                    MODE_KEY, self._id_to_name(props["activeMode"])
                )
            elif "active" in props:
                self._save_and_do_callbacks(MODE_KEY, self._id_to_name(props["active"]))

        # Location mode change.
        # These come in per location and can arrive multiple times per state
        # change. We limit the updates to once per MODE_UPDATE_INTERVAL
        # seconds. Arlo doesn't send a "schedule changed" notification so we
        # re-fetch that information before testing the mode.
        elif resource == "states":
            now = time.monotonic()
            with self._lock:
                if now < self._last_update + MODE_UPDATE_INTERVAL:
                    return
                self._last_update = now
            self._arlo.debug("state change")
            self.update_modes()
            self.update_mode()

        # mode change?
        elif resource == "activeAutomations":
            self._set_mode_or_schedule(event)

        # schedule has changed, so reload
        elif resource == "automationRevisionUpdate":
            self.update_modes()

        # pass on to lower layer
        else:
            super()._event_handler(resource, event)

    @property
    def available_modes(self):
        """Returns string list of available modes.

        For example:: ``['disarmed', 'armed', 'home']``
        """
        return list(self.available_modes_with_ids.keys())

    @property
    def available_modes_with_ids(self):
        """Returns dictionary of available modes mapped to Arlo ids.

        For example:: ``{'armed': 'mode1','disarmed': 'mode0','home': 'mode2'}``
        """
        modes = {}
        for key, mode_id in self._load_matching([MODE_NAME_TO_ID_KEY, "*"]):
            modes[key.split("/")[-1]] = mode_id
        if not modes:
            modes = DEFAULT_MODES
        return modes

    @property
    def gatewayDeviceUniqueIds(self):
        return self._gatewayDeviceUniqueIds

    @property
    def mode(self):
        """Returns the current mode."""
        return self._load(MODE_KEY, "unknown")

    @mode.setter
    def mode(self, mode_name):
        """Set the location mode.

        :param mode_name: mode to use, as returned by available_modes:
        """
        # Actually passed a mode?
        mode_id = None
        real_mode_name = self._id_to_name(mode_name)
        if real_mode_name:
            self._arlo.debug(f"passed an ID({mode_name}), converting it")
            mode_id = mode_name
            mode_name = real_mode_name

        # Need to change?
        if self.mode == mode_name:
            self._arlo.debug("no mode change needed")
            return

        if mode_id is None:
            mode_id = self._name_to_id(mode_name)
        if mode_id:

            # Need to change?
            if self.mode == mode_id:
                self._arlo.debug("no mode change needed (id)")
                return

            # Post change.
            self._arlo.debug(self._location_id + ":new-mode=" + mode_name + ",id=" + mode_id)
            mode_revision = self._load(MODE_REVISION_KEY, 1)
            self._arlo.error("OldRev: {0}".format(mode_revision))

            data = self._arlo.be.put(
                LOCATION_ACTIVEMODE_PATH_FORMAT.format(self._location_id) + "&revision={0}".format(mode_revision),
                {
                    "mode": mode_id,
                })
            
            mode_revision = data.get("revision")
            self._arlo.error("NewRev: {0}".format(mode_revision))

            self._save_and_do_callbacks(MODE_KEY, mode_name)
            self._save(MODE_REVISION_KEY, mode_revision)
                
        else:
            self._arlo.warning(
                "{0}: mode {1} is unrecognised".format(self._location_id, mode_name)
            )


    def update_mode(self):
        """Check and update the base's current mode."""
        now = time.monotonic()
        with self._lock:
            if now < self._last_update + MODE_UPDATE_INTERVAL:
                self._arlo.debug('skipping an update')
                return
            self._last_update = now
        
        data = self._arlo.be.get(LOCATION_ACTIVEMODE_PATH_FORMAT.format(self._location_id))
        properties = data.get("properties", {})
        mode_name = properties.get('mode')
        mode_revision = data.get("revision")
        self._save_and_do_callbacks(MODE_KEY, mode_name)
        self._save(MODE_REVISION_KEY, mode_revision)

    def update_modes(self, initial=False):
        """Get and update the available modes for the base."""
        modes = self._arlo.be.get(
            LOCATION_MODES_PATH_FORMAT.format(self._location_id)
        )
        if modes is not None:
            self._parse_modes(modes.get("properties", {}))
        else:
            self._arlo.error("failed to read modes (v2)")

    def __repr__(self):
        # Representation string of object.
        return "<{0}:{1}:{2}>".format(
            self.__class__.__name__, self._location_id, self._name
        )

    def _to_storage_key(self, attr):
        # Build a key incorporating the type!
        if isinstance(attr, list):
            return [self.__class__.__name__, self._location_id] + attr
        else:
            return [self.__class__.__name__, self._location_id, attr]

    def _event_handler(self, resource, event):
        self._arlo.vdebug("{}: got {} event **".format(self.name, resource))

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
        # TODO only care if it changes?
        self._arlo.st.set(self._to_storage_key(attr), value)

    def _save_and_do_callbacks(self, attr, value):
        self._save(attr, value)
        self._do_callbacks(attr, value)

    def _load(self, attr, default=None):
        return self._arlo.st.get(self._to_storage_key(attr), default)

    def _load_matching(self, attr, default=None):
        return self._arlo.st.get_matching(self._to_storage_key(attr), default)

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