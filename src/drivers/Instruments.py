
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
from pathlib import Path

logger = logging.getLogger(__name__)

def load_instruments():
    """
        Loads the connected instruments into a device dictionnary
    """
    # set devices dict
    devices=defaultdict(dict)
    # initialize cryostat
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
        path_config = Path(r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\config_UdeM.ini")
        #path_config = (r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\config_WFU.ini")
        SLM = Slm(path_config)
        devices['SLM'] = SLM
        logger.info('%s SLM connected' % datetime.datetime.now())
    except Exception as e:
        SLM = SLMDemo()
        devices['SLM'] = SLM
        logger.error('%s SLM initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s SLMDemo connected' % datetime.datetime.now())

    # initialize Stresing & Monochrom
    spectrometers = {}

    try:
        # Path to the configuration folder
        folder_path_config = Path(r"C:\Program Files\Stresing\Escam")

        # Choose the configuration file
        config_name = "config_UdeM.ini"
        # config_name = "config.ini" # WFU path

        # Full path to the configuration file
        path_config = folder_path_config / config_name
        path_config = str(path_config)

        if config_name == "config_UdeM.ini":
            print('Udem Settings Chosen')
            stresing_params = {
                'pixel_size_mm': 24e-3,
                'num_pixels': 1010,
                'calibrated': False,
                'calibrationThirdOrder': 0,
                'calibrationSecondOrder': 0,
                'calibrationFirstOrder': 0.9891,
                'calibrationOffset': -51.163
            }

            grating_params_pixis = {
                    'focal_length_mm':300,
                    'f':np.float64(300000000.0),
                    'delta':np.float64(0.06),
                    'gamma':np.float64(0.5),
                    'n0':np.float64(516.6), # Central pixel
                    'offset_adjust':0,
                    'd_grating':833.3333333333334,
                    'x_pixel':26000,
                    'curvature':np.float64(0.0),
                }

            grating_params = {
                'Stresing': stresing_params,
                'Pixis': grating_params_pixis
            }

            try:
                Monochrom = SpectraPro2300i(grating_params)
                logger.info('%s SpectraPro2300i connected' % datetime.datetime.now())
            except Exception as e:
                Monochrom = SpectraPro2300iDemo(grating_params)
                logger.error('%s SpectraPro2300i initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
                logger.info('%s SpectraPro2300iDemo connected' % datetime.datetime.now())


        else:
            print('WFU Settings Chosen')
            stresing_params = {
                'pixel_size_mm': 24e-3,
                'num_pixels': 1010,
                'calibrated': False,
                'calibrationThirdOrder': -1.29565e-07,
                'calibrationSecondOrder': 0.000165366,
                'calibrationFirstOrder': 0.409445,
                'calibrationOffset': 265.515,
            }

            grating_params = {
                'focal_length_mm': 150,  # should be 150
                'f': np.float64(330000000.08),
                'delta': np.float64(-0.7775441817634736),
                'gamma': np.float64(0.7313712629429233),
                'n0': np.float64(511.0),
                'offset_adjust': 0.0,
                'd_grating': np.float64(3333.3333333333335),
                'x_pixel': 24000.0,
                'curvature': np.float64(-9.999764504749403e-07),
            }

            Monochrom = Shamrock(grating_params)
            logger.info('%s Monochrom DEMO connected' % datetime.datetime.now())

        devices['Monochrom'] = Monochrom
        camera= StresingCamera(stresing_params, path_config)
        camera.attach_to_monochromator(Monochrom)
        spectrometers['Stresing'] = camera
        logger.info('%s Stresing connected' % datetime.datetime.now())
    except Exception as e:
        logger.warning(f'Stresing failed: {e}')

    pixis_params = {
        'pixel_size_mm':26e-3,
        'num_pixels':1024,
        'calibrated':True,
        'calibrationThirdOrder':0,
        'calibrationSlope':0,
        'calibrationOffset':0
    }

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
