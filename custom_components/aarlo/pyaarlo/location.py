from .constant import (
    DEFAULT_MODES,
    MODE_ID_TO_NAME_KEY,
    MODE_KEY,
    MODE_NAME_TO_ID_KEY,
    MODE_UPDATE_INTERVAL,
    LOCATION_MODES_PATH_FORMAT,
    LOCATION_ACTIVEMODE_PATH_FORMAT,
    MODE_REVISION_KEY
)
from .super import ArloSuper


AUTOMATION_ACTIVE_MODE = "automation/activeMode"
AUTOMATION_MODES = "automation/modes"


class ArloLocation(ArloSuper):
    """ Represents a Location object.

    Each Arlo account can have multiple owned locations and multiple shared locations.
    """
    def __init__(self, arlo, attrs):
        super().__init__(attrs.get("locationName", "unknown"), arlo, attrs,
                         id=attrs.get("locationId", "unknown"),
                         type="location")

        self._device_ids = attrs.get("gatewayDeviceIds", [])

        self._last_update = 0

    def _id_to_name(self, mode_id):
        return self._load([MODE_ID_TO_NAME_KEY, mode_id], None)

    def _name_to_id(self, mode_name):
        return self._load([MODE_NAME_TO_ID_KEY, mode_name], None)

    def _parse_modes(self, modes):
        for mode in modes.items():
            mode_id = mode[0]
            mode_name = mode[1].get("name", "")
            if mode_id and mode_name != "":
                self.debug(mode_id + "<=M=>" + mode_name)
                self._save([MODE_ID_TO_NAME_KEY, mode_id], mode_name)
                self._save([MODE_NAME_TO_ID_KEY, mode_name], mode_id)

    def _set_mode_or_schedule(self, event):
        pass

    def _event_handler(self, resource, event):
        self.debug(self.name + " LOCATION got " + resource)

        # A (user requested?) mode change.
        if resource == AUTOMATION_ACTIVE_MODE:
            props = event.get("properties", {})
            mode = props.get("properties", {}).get("mode", None)
            if mode is not None:
                self._save_and_do_callbacks(MODE_KEY, self._id_to_name(mode))
            mode_revision = props.get("revision", None)
            if mode_revision is not None:
                self._save(MODE_REVISION_KEY, mode_revision)

        # A mode list update
        if resource == AUTOMATION_MODES:
            self._parse_modes(event.get("properties", {}).get("properties", {}))

        # A (user requested?) mode change.
        if resource == "states":
            mode = event.get("states", {}).get("activeMode", None)
            if mode is not None:
                self._save_and_do_callbacks(MODE_KEY, self._id_to_name(mode))

        # mode change?
        elif resource == "activeAutomations":
            self._set_mode_or_schedule(event)

        # schedule has changed, so reload
        elif resource == "automationRevisionUpdate":
            self.update_modes()

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
    def device_ids(self):
        return self._device_ids

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
            self.debug(f"passed an ID({mode_name}), converting it")
            mode_id = mode_name
            mode_name = real_mode_name

        # Need to change?
        if self.mode == mode_name:
            self.debug("no mode change needed")
            return

        if mode_id is None:
            mode_id = self._name_to_id(mode_name)
        if mode_id:

            # Need to change?
            if self.mode == mode_id:
                self.debug("no mode change needed (id)")
                return

            # Post change.
            self.debug(self._id + ":new-mode=" + mode_name + ",id=" + mode_id)
            mode_revision = self._load(MODE_REVISION_KEY, 1)
            self.debug("OldRev: {0}".format(mode_revision))

            data = self._arlo.be.put(
                LOCATION_ACTIVEMODE_PATH_FORMAT.format(self._id) + "&revision={0}".format(mode_revision),
                {
                    "mode": mode_id,
                })
            
            mode_revision = data.get("revision")
            self.debug("NewRev: {0}".format(mode_revision))

            self._save_and_do_callbacks(MODE_KEY, mode_name)
            self._save(MODE_REVISION_KEY, mode_revision)
                
        else:
            self._arlo.warning(
                "{0}: mode {1} is unrecognised".format(self._id, mode_name)
            )

    def update_mode(self):
        """Check and update the base's current mode."""
        data = self._arlo.be.get(LOCATION_ACTIVEMODE_PATH_FORMAT.format(self._id))
        properties = data.get("properties", {})
        mode_name = properties.get('mode')
        mode_revision = data.get("revision")
        self._save_and_do_callbacks(MODE_KEY, mode_name)
        self._save(MODE_REVISION_KEY, mode_revision)

    def update_modes(self, _initial=False):
        """Get and update the available modes for the base."""
        modes = self._arlo.be.get(
            LOCATION_MODES_PATH_FORMAT.format(self._id)
        )
        if modes is not None:
            self._parse_modes(modes.get("properties", {}))
        else:
            self._arlo.error("failed to read modes.")
