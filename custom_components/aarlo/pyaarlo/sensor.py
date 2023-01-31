
from .constant import (
    ALS_STATE_KEY,
    BATTERY_KEY,
    CONTACT_STATE_KEY,
    MOTION_DETECTED_KEY,
    MOTION_STATE_KEY,
    TAMPER_STATE_KEY,
    TEMPERATURE_KEY,
    WATER_STATE_KEY,
)
from .device import ArloChildDevice


class ArloSensor(ArloChildDevice):
    def __init__(self, name, arlo, attrs):
        """An Arlo All-in-One Sensor.

        Currently we handle light level, battery, open/close, motion,
        tamper, temperature and water states.

        :param name: name of sensor
        :param arlo: controlling arlo instance
        :param attrs: initial attributes give by Arlo
        """
        super().__init__(name, arlo, attrs)

    @property
    def resource_type(self):
        return "sensors"

    def _event_handler(self, resource, event):
        self.debug(self.name + " SENSOR got one " + resource)

        # pass on to lower layer
        super()._event_handler(resource, event)

    @property
    def has_motion(self):
        return self._load(MOTION_STATE_KEY, False)

    @property
    def is_open(self):
        return self._load(CONTACT_STATE_KEY, False)

    @property
    def is_wet(self):
        return self._load(WATER_STATE_KEY, False)

    @property
    def is_low_light(self):
        return self._load(ALS_STATE_KEY, False)

    @property
    def is_being_tampered_with(self):
        return self._load(TAMPER_STATE_KEY, False)

    @property
    def temperature(self):
        return self._load(TEMPERATURE_KEY, None)

    def has_capability(self, cap):
        if cap in (ALS_STATE_KEY, BATTERY_KEY, CONTACT_STATE_KEY, MOTION_DETECTED_KEY,
                   TAMPER_STATE_KEY, TEMPERATURE_KEY):
            return True
        return False
