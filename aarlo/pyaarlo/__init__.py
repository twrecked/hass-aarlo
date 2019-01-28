
import logging
import time
import datetime
import base64
import pprint
import threading

from custom_components.aarlo.pyarlo.background import ArloBackground
from custom_components.aarlo.pyarlo.storage import ArloStorage
from custom_components.aarlo.pyarlo.backend import ArloBackEnd
from custom_components.aarlo.pyarlo.media import ArloMediaLibrary
from custom_components.aarlo.pyarlo.base import ArloBase
from custom_components.aarlo.pyarlo.camera import ArloCamera
from custom_components.aarlo.pyarlo.doorbell import ArloDoorBell

from custom_components.aarlo.pyarlo.constant import ( BLANK_IMAGE,
                                DEVICE_KEYS,
                                DEVICES_URL,
                                TOTAL_BELLS_KEY,
                                TOTAL_CAMERAS_KEY )

_LOGGER = logging.getLogger('cc.aarlo.pyarlo')

class PyArlo(object):

    def __init__( self,username,password,name='arlo',store='/config/state-arlo' ):
        self._name = name
        self._bg   = ArloBackground( self )
        self._st   = ArloStorage( self,store )
        self._be   = ArloBackEnd( self,username,password )
        self._ml   = ArloMediaLibrary( self )
        self._lock = threading.Lock()
        self._bases     = []
        self._cameras   = []
        self._doorbells = []

        # on day flip we reload image count
        self._today = datetime.date.today()

        # default blank image whe waiting for camera image to appear
        self._blank_image = base64.standard_b64decode( BLANK_IMAGE )

        # slow piece.
        # get devices and fill local db, and create device instance
        self.info('getting devices')
        self._devices = self._be.get( DEVICES_URL )
        self._parse_devices()
        for device in self._devices:
            dname = device.get('deviceName')
            dtype = device.get('deviceType')
            if device.get('state','unknown') != 'provisioned':
                self.info('skipping ' + dname + ': state unknown')
            elif dtype == 'basestation':
                self._bases.append( ArloBase( dname,self,device ) )
            elif dtype == 'camera' or dtype == 'arloq' or dtype == 'arloqs':
                self._cameras.append( ArloCamera( dname,self,device ) )
            elif dtype == 'doorbell':
                self._doorbells.append( ArloDoorBell( dname,self,device ) )

        # save out unchanging stats!
        self._st.set( ['ARLO',TOTAL_CAMERAS_KEY],len(self._cameras) )
        self._st.set( ['ARLO',TOTAL_BELLS_KEY],len(self._doorbells) )

        # queue up initial config retrieval
        self.info('getting initial settings' )
        self._ml.load()
        self._bg.run_in( self._refresh_cameras,1 )
        self._bg.run_in( self._run_every_1,2 )
        self._bg.run_in( self._run_every_15,3 )

        # register house keeping cron jobs
        self.info('registering cron jobs')
        self._bg.run_every( self._run_every_1,1*60 )
        self._bg.run_every( self._run_every_15,15*60 )

    def __repr__(self):
        # Representation string of object.
        return "<{0}: {1}>".format(self.__class__.__name__, self._name)

    def _parse_devices( self ):
        for device in self._devices:
            device_id = device.get('deviceId',None)
            if device_id is not None:
                for key in DEVICE_KEYS:
                    value = device.get(key,None)
                    if value is not None:
                        self._st.set( [device_id,key],value )

    def _refresh_cameras( self ):
        for camera in self._cameras:
            camera.update_last_image()
            camera.update_media()

    def _refresh_bases( self ):
        for base in self._bases:
            self._bg.run( self._be.notify,base=base,body={"action":"get","resource":"modes","publishResponse":False} )
            self._bg.run( self._be.notify,base=base,body={"action":"get","resource":"cameras","publishResponse":False} )
            self._bg.run( self._be.notify,base=base,body={"action":"get","resource":"doorbells","publishResponse":False} )

    def _run_every_1( self ):
        self.info( 'fast refresh' )
        self._st.save()

        # alway ping bases
        for base in self._bases:
            self._bg.run( self._be.ping,base=base )

        # if day changes then reload camera counts
        today = datetime.date.today()
        if self._today != today:
            self.info( 'day changed!' )
            self._refresh_cameras()
            self._today = today

    def _run_every_15( self ):
        self.info( 'slow refresh' )
        self._refresh_bases()
        #self._bg.run( self._ml.load )

    def stop( self ):
        self._st.save()
        self._be.logout()

    @property
    def name( self ):
        return self._name

    @property
    def is_connected( self ):
        return self._be.is_connected()

    @property
    def cameras( self ):
        return self._cameras

    @property
    def doorbells( self ):
        return self._doorbells

    @property
    def base_stations( self ):
        return self._bases

    @property
    def blank_image( self ):
        return self._blank_image

    def lookup_camera_by_id( self,device_id ):
        camera = list(filter( lambda cam: cam.device_id == device_id, self.cameras ))
        if camera:
            return camera[0]
        return None

    def lookup_camera_by_name( self,name ):
        camera = list(filter( lambda cam: cam.name == name, self.cameras ))
        if camera:
            return camera[0]
        return None

    def lookup_doorbell_by_id( self,device_id ):
        doorbell = list(filter( lambda cam: cam.device_id == device_id, self.doorbells ))
        if doorbell:
            return doorbell[0]
        return None

    def lookup_doorbell_by_name( self,name ):
        doorbell = list(filter( lambda cam: cam.name == name, self.doorbells ))
        if doorbell:
            return doorbell[0]
        return None

    def attribute( self,attr ):
        return self._st.get( ['ARLO',attr],None )

    def add_attr_callback( self,attr,cb ):
        pass

    # needs thinking about... track new cameras for example..
    def update(self, update_cameras=False, update_base_station=False):
        pass

    def error( self,msg ):
        _LOGGER.error( msg  )

    def warning( self,msg ):
        _LOGGER.warning( msg  )

    def info( self,msg ):
        _LOGGER.info( msg  )

    def debug( self,msg ):
        _LOGGER.debug( msg  )

