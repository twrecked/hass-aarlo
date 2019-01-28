
import pprint
from custom_components.aarlo.pyarlo.device import ArloChildDevice

class ArloDoorBell(ArloChildDevice):

    def __init__( self,name,arlo,attrs ):
        super().__init__( name,arlo,attrs )

    def _motion_stopped( self ):
        self._save_and_do_callbacks( 'motionDetected',False )

    def _button_unpressed( self ):
        self._save_and_do_callbacks( 'buttonPressed',False )

    def _event_handler( self,resource,event ):
        self._arlo.info( self.name + ' DOORBELL got one ' + resource )

        # create fake motion/button press event...
        if resource.startswith('doorbells/'):
            cons = event.get('properties',{}).get('connectionState',False)
            butp = event.get('properties',{}).get('buttonPressed',False)
            #acts = event.get('properties',{}).get('activityState',False)
            if cons and cons == 'available':
                self._save_and_do_callbacks( 'motionDetected',True )
                self._arlo._bg.run_in( self._motion_stopped,15 )
            if butp:
                self._save_and_do_callbacks( 'buttonPressed',True )
                self._arlo._bg.run_in( self._button_unpressed,5 )
            #  if acts and acts == 'idle':
                #  self._save_and_do_callbacks( 'motionDetected',False )
                #  self._save_and_do_callbacks( 'buttonPressed',False )

        # pass on to lower layer
        super()._event_handler( resource,event )

    def has_capability( self,cap ):
        if cap.startswith( 'button' ):
            return True
        return super().has_capability( cap )

