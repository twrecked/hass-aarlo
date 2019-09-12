
from .device import ArloChildDevice


class ArloLight(ArloChildDevice):

    def __init__(self, name, arlo, attrs):
        super().__init__(name, arlo, attrs)

    @property
    def resource_type(self):
        return "lights"

    def _event_handler(self, resource, event):
        self._arlo.debug(self.name + ' LIGHT got one ' + resource)

        if resource == self.resource_id:
            lamp = event.get('properties', {}).get('lampState', "off")
            self._save_and_do_callbacks('lampState', lamp)

        # pass on to lower layer
        super()._event_handler(resource, event)

