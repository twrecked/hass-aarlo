import pprint
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import PyArlo

from .constant import (
    AIR_QUALITY_KEY,
    AUTOMATION_PATH,
    CONNECTION_KEY,
    DEFAULT_MODES,
    DEFINITIONS_PATH,
    HUMIDITY_KEY,
    MODE_ID_TO_NAME_KEY,
    MODE_IS_SCHEDULE_KEY,
    MODE_KEY,
    MODE_NAME_TO_ID_KEY,
    MODE_UPDATE_INTERVAL,
    MODEL_BABY,
    MODEL_ESSENTIAL,
    MODEL_GO,
    MODEL_HUB,
    MODEL_PRO_3_FLOODLIGHT,
    MODEL_PRO_4,
    MODEL_WIRED_VIDEO_DOORBELL,
    MODEL_WIREFREE_VIDEO_DOORBELL,
    PING_CAPABILITY,
    RESOURCE_CAPABILITY,
    RESTART_PATH,
    SCHEDULE_KEY,
    SIREN_STATE_KEY,
    TEMPERATURE_KEY,
    TIMEZONE_KEY
)
from .device import ArloDevice
from .util import time_to_arlotime

day_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su", "Mo"]


class ArloBase(ArloDevice):
    def __init__(self, name: str, arlo: 'PyArlo', attrs):
        super().__init__(name, arlo, attrs)
        self._refresh_rate = 15
        self._schedules = None
        self._last_update = 0

    def _id_to_name(self, mode_id):
        return self._load([MODE_ID_TO_NAME_KEY, mode_id], None)

    def _id_is_schedule(self, mode_id):
        return self._load([MODE_IS_SCHEDULE_KEY, mode_id.lower()], False)

    def _name_to_id(self, mode_name):
        return self._load([MODE_NAME_TO_ID_KEY, mode_name.lower()], None)

    def _parse_modes(self, modes):
        for mode in modes:
            mode_id = mode.get("id", None)
            mode_name = mode.get("name", "")
            if mode_name == "":
                mode_name = mode.get("type", "")
                if mode_name == "":
                    mode_name = mode_id
            if mode_id and mode_name != "":
                self._arlo.debug(mode_id + "<=M=>" + mode_name)
                self._save([MODE_ID_TO_NAME_KEY, mode_id], mode_name)
                self._save([MODE_NAME_TO_ID_KEY, mode_name.lower()], mode_id)
                self._save([MODE_IS_SCHEDULE_KEY, mode_id.lower()], False)
                self._save([MODE_IS_SCHEDULE_KEY, mode_name.lower()], False)

    def schedule_to_modes(self):
        if self._schedules is None:
            return []

        now = time.localtime()
        day = day_of_week[now.tm_wday]
        minute = (now.tm_hour * 60) + now.tm_min
        for schedule in self._schedules:
            if not schedule.get("enabled", False):
                continue
            for action in schedule.get("schedule", []):
                if day in action.get("days", []):
                    start = action.get("startTime", 65535)
                    duration = action.get("duration", 65536)
                    if start <= minute < (start + duration):
                        modes = action.get("startActions", {}).get("enableModes", None)
                        if modes:
                            self._arlo.debug("schdule={}".format(modes[0]))
                            return modes

        # If nothing in schedule we are disarmed.
        return ["mode0"]

    def _parse_schedules(self, schedules):
        self._schedules = schedules
        for schedule in schedules:
            schedule_id = schedule.get("id", None)
            schedule_name = schedule.get("name", "")
            if schedule_name == "":
                schedule_name = schedule_id
            if schedule_id and schedule_name != "":
                self._arlo.debug(schedule_id + "<=S=>" + schedule_name)
                self._save([MODE_ID_TO_NAME_KEY, schedule_id], schedule_name)
                self._save([MODE_NAME_TO_ID_KEY, schedule_name.lower()], schedule_id)
                self._save([MODE_IS_SCHEDULE_KEY, schedule_id.lower()], True)
                self._save([MODE_IS_SCHEDULE_KEY, schedule_name.lower()], True)

    def _set_mode_or_schedule(self, event):
        
        # schedule on or off?
        schedule_ids = event.get("activeSchedules", [])
        if schedule_ids:
            self._arlo.debug(self.name + " schedule change " + schedule_ids[0])
            schedule_name = self._id_to_name(schedule_ids[0])
            self._save_and_do_callbacks(SCHEDULE_KEY, schedule_name)
        else:
            self._arlo.debug(self.name + " schedule cleared ")
            self._save_and_do_callbacks(SCHEDULE_KEY, None)

        # mode present? we just set to that one... If no mode but schedule then
        # try to parse that out
        mode_ids = event.get("activeModes", [])
        if not mode_ids and schedule_ids:
            self._arlo.debug(self.name + " mode change (via schedule) ")
            self._arlo.vdebug(
                self.name + " schedules: " + pprint.pformat(self._schedules)
            )
            mode_ids = self.schedule_to_modes()
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

        # Base station mode change.
        # These come in per device and can arrive multiple times per state
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
    def _modes_version(self):
        if self._arlo.cfg.mode_api.lower() == "v1":
            self._arlo.vdebug("forced v1 api")
            return 1
        if self._arlo.cfg.mode_api.lower() == "v2":
            self._arlo.vdebug("forced v2 api")
            return 2
        if self._arlo.cfg.mode_api.lower() == "v3":
            self._arlo.vdebug("forced v3 api")
            return 3
        if self._arlo.be.multi_location:
            self._arlo.debug("multilocation, deduced v3 api")
            return 3
        if (
            self.model_id == MODEL_BABY
            or self.model_id == MODEL_GO
            or self.device_type == "arloq"
            or self.device_type == "arloqs"
        ):
            self._arlo.vdebug("deduced v1 api")
            return 1
        self._arlo.vdebug("deduced v2 api")
        return 2

    @property
    def _v1_modes(self):
        return self._modes_version == 1
        
    @property
    def _v2_modes(self):
        return self._modes_version == 2

    @property
    def _v3_modes(self):
        return self._modes_version == 3

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
    def mode(self):
        """Returns the current mode."""
        return self._load(MODE_KEY, "unknown")

    @mode.setter
    def mode(self, mode_name):
        """Set the base station mode.

        **Note:** Setting mode has been known to hang, method includes code to
        keep retrying.

        :param mode_name: mode to use, as returned by available_modes:
        """
        if self._v3_modes:
            self._arlo.debug(f"BaseStations don't have modes in v3")
            return

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

            if not self._v3_modes:
                # Schedule or mode? Manually set schedule key.
                if self._id_is_schedule(mode_id):
                    active = "activeSchedules"
                    inactive = "activeModes"
                    self._save_and_do_callbacks(SCHEDULE_KEY, mode_name)
                else:
                    active = "activeModes"
                    inactive = "activeSchedules"
                    self._save_and_do_callbacks(SCHEDULE_KEY, None)

            # Post change.
            self._arlo.debug(self.name + ":new-mode=" + mode_name + ",id=" + mode_id)
            if self._v1_modes:
                self._arlo.be.notify(
                    base=self,
                    body={
                        "action": "set",
                        "resource": "modes",
                        "publishResponse": True,
                        "properties": {"active": mode_id},
                    },
                )
            elif self._v2_modes:
                # This is complicated... Setting a mode can fail and setting a mode can be sync or async.
                # This code tried 3 times to set the mode with attempts to reload the devices between
                # attempts to try and kick Arlo. In async mode the first set works in the current thread,
                # subsequent ones run in the background. In sync mode it the same. Sorry.
                def _set_mode_v2_cb(attempt):
                    self._arlo.debug("v2 arming")
                    params = {
                        "activeAutomations": [
                            {
                                "deviceId": self.device_id,
                                "timestamp": time_to_arlotime(),
                                active: [mode_id],
                                inactive: [],
                            }
                        ]
                    }
                    if attempt < 4:
                        tid = "(modes:{}|activeAutomations)".format(self.device_id)
                        body = self._arlo.be.post(
                            AUTOMATION_PATH,
                            params=params,
                            raw=True,
                            tid=tid,
                            wait_for=None,
                        )
                        if body is not None:
                            if (
                                body.get("success", False) is True
                                or body.get("resource", "") == "modes"
                                or body.get("resource", "") == "activeAutomations"
                            ):
                                return
                        self._arlo.warning(
                            "attempt {0}: error in response when setting mode=\n{1}".format(
                                attempt, pprint.pformat(body)
                            )
                        )
                        self._arlo.debug(
                            "Fetching device list (hoping this will fix arming/disarming)"
                        )
                        self._arlo.be.devices()
                        if self._arlo.cfg.synchronous_mode:
                            self._arlo.debug("trying again, but synchronous")
                            _set_mode_v2_cb(attempt=attempt + 1)
                        else:
                            self._arlo.bg.run(_set_mode_v2_cb, attempt=attempt + 1)
                        return

                    self._arlo.error("Failed to set mode.")
                    self._arlo.debug(
                        "Giving up on setting mode! Session headers=\n{}".format(
                            pprint.pformat(self._arlo.be.session.headers)
                        )
                    )
                    self._arlo.debug(
                        "Giving up on setting mode! Session cookies=\n{}".format(
                            pprint.pprint(self._arlo.be.session.cookies)
                        )
                    )

                _set_mode_v2_cb(1)
            else:
                self._arlo.be.put(
                    base=self,
                    body={
                        "action": "set",
                        "resource": "modes",
                        "publishResponse": True,
                        "properties": {"active": mode_id},
                    })
                    
        else:
            self._arlo.warning(
                "{0}: mode {1} is unrecognised".format(self.name, mode_name)
            )

    def update_mode(self):
        """Check and update the base's current mode."""
        now = time.monotonic()
        with self._lock:
            #  if now < self._last_update + MODE_UPDATE_INTERVAL:
            #  self._arlo.debug('skipping an update')
            #  return
            self._last_update = now
        
        if not self._v3_modes:
            data = self._arlo.be.get(AUTOMATION_PATH)
            for mode in data:
                if mode.get("uniqueId", "") == self.unique_id:
                    self._set_mode_or_schedule(mode)

    def update_modes(self, initial=False):
        """Get and update the available modes for the base."""
        if self._v1_modes:
            # Work around slow arlo connections.
            if initial and self._arlo.cfg.synchronous_mode:
                time.sleep(5)
            resp = self._arlo.be.notify(
                base=self,
                body={"action": "get", "resource": "modes", "publishResponse": False},
                wait_for="event",
            )
            if resp is not None:
                props = resp.get("properties", {})
                self._parse_modes(props.get("modes", []))
            else:
                self._arlo.error("unable to read mode, try forcing v2")
        elif self._v2_modes:
            modes = self._arlo.be.get(
                DEFINITIONS_PATH + "?uniqueIds={}".format(self.unique_id)
            )
            if modes is not None:
                modes = modes.get(self.unique_id, {})
                self._parse_modes(modes.get("modes", []))
                self._parse_schedules(modes.get("schedules", []))
                self._save(TIMEZONE_KEY, modes.get("olsonTimeZone", None))
            else:
                self._arlo.error("failed to read modes (v2)")
        else:
            self._arlo.debug("V3Modes - None on BaseStation")
            curr_location = None
            for location in self._arlo.locations:
                for device_id in location.device_ids:
                    if device_id == self.unique_id:
                        curr_location = location
                        break
                if curr_location is not None:
                    break
            if curr_location:
                curr_location.update_mode()

    def update_states(self):
        # Only do work on 'old' style base stations
        if self.device_type == 'basestation' or self.device_type == 'arlobridge':
            self.debug("updating state")
            self._arlo.be.notify(
                base=self,
                body={
                    "action": "get",
                    "resource": "devices",
                    "publishResponse": False,
                },
                wait_for="response",
            )

    @property
    def schedule(self):
        """Returns current schedule name or `None` if no schedule active."""
        return self._load(SCHEDULE_KEY, None)

    @property
    def on_schedule(self):
        """Returns `True` is base station is running a schedule."""
        return self.schedule is not None

    @property
    def refresh_rate(self):
        return self._refresh_rate

    @refresh_rate.setter
    def refresh_rate(self, value):
        if isinstance(value, (int, float)):
            self._refresh_rate = value

    @property
    def siren_state(self):
        """Returns the current siren state (`on` or `off`)."""
        return self._load(SIREN_STATE_KEY, "off")

    def siren_on(self, duration=300, volume=8):
        """Turn base siren on.

        Does nothing if base doesn't support sirens.

        :param duration: how long, in seconds, to sound for
        :param volume: how long, from 1 to 8, to sound
        """
        body = {
            "action": "set",
            "resource": "siren",
            "publishResponse": True,
            "properties": {
                "sirenState": "on",
                "duration": int(duration),
                "volume": int(volume),
                "pattern": "alarm",
            },
        }
        self._arlo.debug(str(body))
        self._arlo.be.notify(base=self, body=body)

    def siren_off(self):
        """Turn base siren off.

        Does nothing if base doesn't support sirens.
        """
        body = {
            "action": "set",
            "resource": "siren",
            "publishResponse": True,
            "properties": {"sirenState": "off"},
        }
        self._arlo.debug(str(body))
        self._arlo.be.notify(base=self, body=body)

    def restart(self):
        params = {"deviceId": self.device_id}
        tid = "diagnostics:{}".format(self.device_id)
        if (
            self._arlo.be.post(RESTART_PATH, params=params, tid=tid, wait_for=None)
            is None
        ):
            self._arlo.debug("RESTART didnt send")

    def _ping_and_check_reply(self):
        body = {
            "action": "set",
            "resource": self._arlo.be.sub_id,
            "publishResponse": False,
            "properties": {"devices": [self.device_id]},
        }
        self._arlo.debug("pinging {}".format(self.name))
        if self._arlo.be.notify(base=self, body=body, wait_for="response") is None:
            self._save_and_do_callbacks(CONNECTION_KEY, "unavailable")
        else:
            self._save_and_do_callbacks(CONNECTION_KEY, "available")

    def ping(self):
        self._arlo.bg.run(self._ping_and_check_reply)

    @property
    def state(self):
        if self.is_unavailable:
            return "unavailable"
        return "available"

    def has_capability(self, cap):
        if cap in (TEMPERATURE_KEY, HUMIDITY_KEY, AIR_QUALITY_KEY):
            if self.model_id.startswith(MODEL_BABY):
                return True
        if cap in (SIREN_STATE_KEY,):
            if (
                self.model_id.startswith(("VMB400", "VMB450"))
                or self.model_id == MODEL_GO
            ):
                return True

        if cap in (PING_CAPABILITY,):

            # Always true for these devices.
            if self.model_id.startswith(MODEL_BABY):
                return True
            if self.model_id.startswith(MODEL_WIRED_VIDEO_DOORBELL):
                return True

            # Don't ping these devices ever.
            if self.model_id.startswith(
                    (MODEL_WIREFREE_VIDEO_DOORBELL, MODEL_ESSENTIAL, MODEL_PRO_3_FLOODLIGHT, MODEL_PRO_4)
            ):
                return False

            # We have to be careful pinging some base stations because it can rapidly
            # drain the battery power. Don't ping if:
            # - it is a device that acts as its own base station
            # - it does not have a power supply or charger connected
            # - it is using WiFi directly rather than an Arlo base station
            if self.is_own_parent:
                if not self.is_corded and not self.has_charger:
                    if self.using_wifi:
                        return False

            return True

        if cap in (RESOURCE_CAPABILITY,):
            # Not all devices need (or want) to get their resources queried.
            if self.model_id.startswith(
                (
                    MODEL_WIREFREE_VIDEO_DOORBELL,
                    MODEL_ESSENTIAL,
                )
            ):
                return False
            return True
        return super().has_capability(cap)
