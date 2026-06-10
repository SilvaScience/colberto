
import logging
import datetime
import numpy as np
from collections import defaultdict
from drivers.CryoDemo import CryoDemo
from drivers.SpectrometerDemo_advanced import SpectrometerDemo
from drivers.SLM import Slm
from drivers.SLMDemo import SLMDemo
from drivers.Stresing import StresingCamera
from drivers.Shamrock import Shamrock 
from drivers.Pixis import Pixis
from drivers.SpectraPro2300i import SpectraPro2300i

logger = logging.getLogger(__name__)

def load_instruments():
    """
        Loads the connected instruments into a device dictionnary
    """

    # set devices dict
    devices=defaultdict(dict)

    # initialize cryostat
    """ This is a demo devices that has read and write parameters. 
    Illustrates use of parameters"""
    # always try to include communication on important events.
    # This is extremely useful for debugging and troubleshooting.
    logger.warning('%s You are using a DEMO version of the cryostat'%datetime.datetime.now())
    cryostat = CryoDemo() # launch cryostat interface
    devices['cryostat'] = cryostat # store in global device dict.

    # initialize SLM
    try:
        #raise Exception('DEMO')
        SLM = Slm()
        devices['SLM'] = SLM
        logger.info('%s SLM connected' % datetime.datetime.now())
    except Exception as e:
        SLM = SLMDemo()
        devices['SLM'] = SLM
        logger.error('%s SLM initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s SLMDemo connected' % datetime.datetime.now())

    # initialize MonochromDemo
    # Shamrock grating parameters
    grating_params={
        'focal_length_mm':163,
        'delta':np.float64(-0.20488367116307532),
        'gamma':np.float64(2.021864300924973),
        'n0':np.float64(511.0), # Central pixel
        'offset_adjust':0,
        'd_grating':np.float64(6666.666666666667),
        'x_pixel':26000.0,
        'curvature':np.float64(3.1224154313329654e-06),
    }
    # SpectraPro 2300i grating parameters
    grating_params = {
        'focal_length_mm':300,
        'delta':np.float64(0),
        'gamma':np.float64(0),
        'n0':np.float64(511.0), # Central pixel
        'offset_adjust':0,
        'd_grating':None,
        'x_pixel':None,
        'curvature':np.float64(0),
    }
    Monochrom = SpectraPro2300i(grating_params) 

    
    
    devices['Monochrom'] = Monochrom 
    logger.info('%s Monochrom DEMO connected' % datetime.datetime.now())

    # initialize Cameras
    stresing_params={
        'pixel_size_mm':24e-3,
        'num_pixels':1010,
        'calibrated': False,
        'calibrationThirdOrder': -3e-5,
        'calibrationSlope': 0.9891,
        'calibrationOffset': -51.163
    }
    pixis_params = {
        'pixel_size_mm':26e-3,
        'num_pixels':1024,
        'calibrated':False,
        'calibrationThirdOrder':0,
        'calibrationSlope':0,
        'calibrationOffset':0
    }

    spectrometers = {}
    
    try:
        camera= StresingCamera(stresing_params)
        camera.attach_to_monochromator(Monochrom)
        spectrometers['Stresing'] = camera
        logger.info('%s Stresing connected' % datetime.datetime.now())
    except Exception as e:
        logger.warning(f'Stresing failed: {e}')

    try:
        camera = Pixis(pixis_params)
        spectrometers['Pixis'] = camera
        camera.attach_to_monochromator(Monochrom)
        logger.info('%s Pixis connected' % datetime.datetime.now())
    except Exception as e:
        logger.warning(f'Pixis failed: {e}')

    try:
        from drivers.OceanSpectrometer import OceanSpectrometer
        ocean = OceanSpectrometer()
        ocean.start()
        spectrometers['Ocean'] = ocean
        logger.info('%s Ocean connected' % datetime.datetime.now())
    except Exception as e:
        logger.warning(f'Ocean failed: {e}')

    try:
        demo = SpectrometerDemo()
        spectrometers['Demo'] = demo
        logger.info('%s Demo spectrometer loaded' % datetime.datetime.now())
    except Exception as e:
        logger.warning(f'Demo failed: {e}')

    #  Choose a default spectrometer (object only)
    if 'Ocean' in spectrometers:
        default_spec = spectrometers['Ocean']
    elif 'Stresing' in spectrometers:
        default_spec = spectrometers['Stresing']
    elif 'Demo' in spectrometers:
        default_spec = spectrometers['Demo']
    else:
        default_spec = None

    # Only store *object* in devices
    devices['spectrometer'] = default_spec

    # Return both — object dicts only
    return devices, spectrometers

