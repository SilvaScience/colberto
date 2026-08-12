
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
from drivers.Optidry250 import CryoPasqal
from drivers.Pixis import Pixis
from drivers.SpectraPro2300i import SpectraPro2300i
from drivers.SpectraPro2300iDemo import SpectraPro2300iDemo

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
    

    try: 
        cryostat = CryoPasqal() # launch cryostat interface
        devices['cryostat'] = cryostat # store in global device dict.
        logger.info('%s Pascal_Cryo connected' % datetime.datetime.now())
    except Exception as e:
        cryostat = CryoDemo() # launch cryostat interface
        devices['cryostat'] = cryostat # store in global device dict.
        logger.error('%s Pascal Cryostat initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s CryoDemo connected' % datetime.datetime.now())






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
    grating_params_stresing={
        '1':{#NOT CALIBRATED
        'focal_length_mm':300,
        'f':np.float64(305381928.6149399),
        'delta':np.float64(0.11432112488955509),
        'gamma':np.float64(0.5337955112241486),
        'n0':np.float64(539.4), # Central pixel
        'offset_adjust':0,
        'd_grating':833.3333333333334,
        'x_pixel':24000.0,
        'curvature':np.float64(5.736575254871788e-07),
        },
        '2':{#NOT CALIBRATED
        'focal_length_mm':300,
        'f':np.float64(305381928.6149399),
        'delta':np.float64(0.11432112488955509),
        'gamma':np.float64(0.5337955112241486),
        'n0':np.float64(539.4), # Central pixel
        'offset_adjust':0,
        'd_grating':833.3333333333334,
        'x_pixel':24000.0,
        'curvature':np.float64(5.736575254871788e-07),
        },
        '3':{#NOT CALIBRATED
        'focal_length_mm':300,
        'f':np.float64(305381928.6149399),
        'delta':np.float64(0.11432112488955509),
        'gamma':np.float64(0.5337955112241486),
        'n0':np.float64(539.4), # Central pixel
        'offset_adjust':0,
        'd_grating':833.3333333333334,
        'x_pixel':24000.0,
        'curvature':np.float64(5.736575254871788e-07),
        }
    }
    f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(330605663.74965495), np.float64(-0.20488367116307532), np.float64(2.021864300924973), np.float64(508.0), 0, 6666.666666666667, 26000.0, np.float64(3.1224154313329654e-06)]
    gratings_params_pixis ={ 
            '1':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta':np.float64(0.5),
                'gamma':np.float64(0.1),
                'n0':np.float64(480.14285714285717), # Central pixel
                'offset_adjust':0,
                'd_grating':833.3333333333334,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(300),
                },
            '2':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta':np.float64(0.5),
                'gamma':np.float64(0.1),
                'n0':np.float64(480.14285714285717), # Central pixel
                'offset_adjust':0,
                'd_grating':833.3333333333334,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(750),
                },
            '3':{
                'focal_length_mm':300,
                'f':np.float64(300000000.0),
                'delta': np.float64(0.05),
                'gamma':np.float64(0.01),
                'n0':np.float64(478.2), # Central pixel
                'offset_adjust':0,
                'd_grating': 3333.333333333333,
                'x_pixel':26000,
                'curvature':np.float64(0.0),
                'blaze':np.float64(2000),
                },
            }
    grating_params = {
        'Stresing': grating_params_stresing,
        'Pixis': gratings_params_pixis
    }
    port='COM5'
    try:
        Monochrom = SpectraPro2300i(grating_params,port=port)
        logger.info('%s SpectraPro2300i connected' % datetime.datetime.now())
    except Exception as e:
        Monochrom = SpectraPro2300iDemo(grating_params)
        logger.error('%s SpectraPro2300i initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s SpectraPro2300iDemo connected' % datetime.datetime.now())

    devices['Monochrom'] = Monochrom

    # initialize Cameras
    stresing_params={
        'pixel_size_mm':24e-3,
        'num_pixels':1010,
        'calibrated': True,
        'calibrationThirdOrder': -3e-5,
        'calibrationSlope': 0.9891,
        'calibrationOffset': -51.163
    }
    pixis_params = {
        'pixel_size_mm':26e-3,
        'num_pixels':1024,
        'calibrated':True,
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

