
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

    # -------------------------------------------------------------------------
    # Initialize crostat
    # -------------------------------------------------------------------------
    try:
        cryostat = CryoPasqal() # launch cryostat interface
        devices['cryostat'] = cryostat # store in global device dict.
        logger.info('%s Pascal_Cryo connected' % datetime.datetime.now())
    except Exception as e:
        cryostat = CryoDemo() # launch cryostat interface
        devices['cryostat'] = cryostat # store in global device dict.
        logger.error('%s Pascal Cryostat initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s CryoDemo connected' % datetime.datetime.now())

    # -------------------------------------------------------------------------
    # Initialize SLM
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Initialize SP2150 Monochromator & Stresing Camera
    # -------------------------------------------------------------------------
    spectrometers = {}

    try:
        # Path to the configuration folder
        folder_path_config = Path(r"C:\Program Files\Stresing\Escam")

        # Choose the configuration file
        config_name = "config_UdeM.ini"
        #config_name = "config.ini" # WFU path

        # Full path to the configuration file
        path_config = folder_path_config / config_name
        path_config = str(path_config)

        if config_name == "config_UdeM.ini":
            print('Udem Settings Chosen')
            stresing_params = {
                'pixel_size_mm': 24e-3,
                'num_pixels': 1010,
                'calibrated': True,
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
            spectrometer_port='COM5'
            grating_params = {
                'Stresing': stresing_params,
                'Pixis': grating_params_pixis
            }

            try:
                Monochrom = SpectraPro2300i(grating_params,port=spectrometer_port)
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
                'calibrated': True,
                'calibrationThirdOrder': -3e-5,
                'calibrationSlope': 0.9891,
                'calibrationOffset': -51.163
            }

            grating_params_sp2150 = {
                '1': {
                    ### Calibrated!! ###  ### 300 g/mm Blaze = 300 nm ###
                    'focal_length_mm': 150,
                    'f': np.float64(162398161.2027362),      # Nominal 150 mm in nm
                    'delta': np.float64(-0.09993658218059505),          # No detector tilt assumed
                    'gamma': np.float64(0.3499999999999999),       # Nominal Acton inclusion angle (~13.0 degrees in rad)
                    'n0': np.float64(497.2),           # Center pixel of 1010 px sensor
                    'offset_adjust': 0.0,
                    'd_grating': np.float64(3333.3333333333335),
                    'x_pixel': 24000.0,
                    'curvature': np.float64(1.1093791606114813e-06),
                }, ### [162398161.2027362, -0.09993658218059505, 0.3499999999999999, 497.2, 0.0, 3333.3333333333335, 24000.0, 1.1093791606114813e-06]

                '2': {
                    ### CALIBRATED!! ###  ###300 g/mm Blaze = 500 nm ###
                    'focal_length_mm': 150,
                    'f': np.float64(162502227.2266555),  # Update after calibration notebook run
                    'delta': np.float64(-0.09999999994609458),
                    'gamma': np.float64(0.3499999999999999),
                    'n0': np.float64(496.4),
                    'offset_adjust': 0.0,
                    'd_grating': np.float64(3333.3333333333335),
                    'x_pixel': 24000.0,
                    'curvature': np.float64(6.343720796893214e-08),

                } ## [162502227.2266555, -0.09999999994609458, 0.3499999999999999, 496.4, 0.0, 3333.3333333333335, 24000.0, 6.343720796893214e-08]
            }

            grating_params = {
                'Stresing': grating_params_sp2150
            }

            spectrometer_port = 'COM4'

            print(f"Connecting SP2150 Monochromator on {spectrometer_port}...")
            try:
                Monochrom = SpectraPro2300i(grating_params, port=spectrometer_port)
                logger.info('SP2150 Monochromator connected on %s' % spectrometer_port)
                print("Monochromator connected successfully.")
            except Exception as e:
                Monochrom = SpectraPro2300iDemo(grating_params)
                logger.error('SP2150 initialization failed: %s' % str(e))
                print(f"Monochromator initialization failed ({e}), loaded Demo.")

            devices['Monochrom'] = Monochrom

            print("Initializing Stresing Camera...")
            try:
                camera = StresingCamera(stresing_params, path_config)
                camera.attach_to_monochromator(Monochrom)
                spectrometers['Stresing'] = camera
                logger.info('Stresing camera connected successfully.')
                print("Stresing Camera connected and attached successfully.")
            except Exception as e:
                logger.warning(f'Stresing camera failed to connect: {e}')
                print(f"Stresing camera failed: {e}")

    except Exception as e:
        logger.error(f'Initialization block error: {e}')

    # -------------------------------------------------------------------------
    # Initialize Auxiliary Cameras
    # -------------------------------------------------------------------------
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
