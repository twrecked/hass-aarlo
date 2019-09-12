
from .constant import LAMP_STATE_KEY
from .device import ArloChildDevice


class ArloLight(ArloChildDevice):

    def __init__(self, name, arlo, attrs):
        super().__init__(name, arlo, attrs)

    @property
    def resource_type(self):
        return "lights"

    def _event_handler(self, resource, event):
        self._arlo.debug(self.name + ' LIGHT got one ' + resource)

        # Get light state.
        if resource == self.resource_id:
            lamp = event.get('properties', {}).get(LAMP_STATE_KEY, "off")
            self._save_and_do_callbacks(LAMP_STATE_KEY, lamp)

        # pass on to lower layer
        super()._event_handler(resource, event)

    @property
    def is_on(self):
        return self._arlo.st.get([self._device_id, LAMP_STATE_KEY], "off") == "on"

    def turn_on(self):
        self._arlo.bg.run(self._arlo.be.notify,
                          base=self.base_station,
                          body={
                              'action': 'set',
                              'properties': {LAMP_STATE_KEY: 'on'},
                              'publishResponse': True,
                              'resource': self.resource_id,
                          })
        return True

    def turn_off(self):
        self._arlo.bg.run(self._arlo.be.notify,
                          base=self.base_station,
                          body={
                              'action': 'set',
                              'properties': {LAMP_STATE_KEY: 'off'},
                              'publishResponse': True,
                              'resource': self.resource_id,
                          })
        return True
