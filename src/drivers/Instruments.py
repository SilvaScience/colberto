
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
    try:
        from drivers.OceanSpectrometer import OceanSpectrometer
        spectrometer = OceanSpectrometer()
        spectrometer.start()
        spec_length = spectrometer.spec_length
        devices['spectrometers'] = spectrometer
        logger.warning('%s Spectrometer Connected' % datetime.datetime.now())
    except:
        spectrometer = SpectrometerDemo()
        spec_length = spectrometer.spec_length
        devices['spectrometers'] = spectrometer
        logger.warning('%s Spectrometer connection failed, use DEMO' % datetime.datetime.now())

    # initialize SLM
    try:
        #raise Exception('DEMO')
        SLM = Slm()
        devices['SLM'] = SLM
        logger.info('%s SLM connected' % datetime.datetime.now())
    except Exception as e:
        SLM = SLMDemo()
        devices['SLM'] = SLM
        logger.error('%s SLM initialization failed at interface startup. Error type %s'%(datetime.datetime.now(),str(e)))
        logger.info('%s SLMDemo connected'%datetime.datetime.now())

    # initialize MonochromDemo
    grating_params={
        'focal_length_mm':150,
        'f':np.float64(330605663.74965495),
        'delta':np.float64(-0.20488367116307532),
        'gamma':np.float64(2.021864300924973),
        'n0':np.float64(508.0),
        'offset_adjust':0,
        'd_grating':np.float64(6666.666666666667),
        'x_pixel':26000.0,
        'curvature':np.float64(3.1224154313329654e-06),
    }
    Monochrom = Shamrock(grating_params) 
    devices['Monochrom'] = Monochrom 
    logger.info('%s Monochrom DEMO connected'%datetime.datetime.now())

    # initialize StresingDemo
    stresing_params={
        'pixel_size_mm':24e-3,
        'num_pixels':1024,
    }
    camera= StresingCamera(stresing_params)
    camera.attach_to_monochromator(Monochrom)
    devices['Stresing'] = camera
    logger.info('%s Stresing connected'%datetime.datetime.now())

    return devices