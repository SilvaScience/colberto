
import datetime
import logging
from collections import defaultdict

from configuration import csv_values, hardware_parameters, load_site_config
from drivers.CryoDemo import CryoDemo
from drivers.Optidry250 import CryoPasqal
from drivers.Pixis import Pixis
from drivers.SLM import Slm
from drivers.SLMDemo import SLMDemo
from drivers.Shamrock import Shamrock
from drivers.SpectraPro2300i import SpectraPro2300i
from drivers.SpectraPro2300iDemo import SpectraPro2300iDemo
from drivers.SpectrometerDemo_advanced import SpectrometerDemo
from drivers.Stresing import StresingCamera

logger = logging.getLogger(__name__)


def _enabled(config, device):
    return config.getboolean("devices", device)


def _camera_parameters(config, section, optics_section):
    parameters = hardware_parameters(config, section)
    parameters.update(hardware_parameters(config, optics_section))
    return parameters


def _load_monochromator(config, grating_parameters):
    if not _enabled(config, "monochromator"):
        raise RuntimeError("Monochromator is required by the configured cameras")
    driver = config.get("monochromator", "driver").strip().lower()
    if driver == "spectrapro2300i":
        try:
            monochromator = SpectraPro2300i(
                grating_parameters,
                port=config.get("monochromator", "serial_port"),
                baud_rate=config.getint("monochromator", "baud_rate"),
            )
            logger.info("%s SpectraPro2300i connected", datetime.datetime.now())
            return monochromator
        except Exception as error:
            logger.error(
                "%s SpectraPro2300i initialization failed at interface startup. Error type %s",
                datetime.datetime.now(), error,
            )
            logger.info("%s SpectraPro2300iDemo connected", datetime.datetime.now())
            return SpectraPro2300iDemo(grating_parameters)
    if driver == "shamrock":
        return Shamrock(
            grating_parameters,
            center_wavelength=config.getfloat("monochromator", "center_wavelength"),
            grating_densities=csv_values(config, "monochromator", "grating_densities", float),
        )
    raise ValueError("Unsupported monochromator driver: %s" % driver)


def load_instruments(site_config=None):
    """
        Loads the connected instruments into a device dictionnary
    """
    config = site_config or load_site_config()
    logger.info("Using Colberto site configuration: %s", config.get("site", "name"))
    devices=defaultdict(dict)
    # initialize cryostat
    try:
        if not _enabled(config, "cryostat"):
            raise RuntimeError("disabled by site configuration")
        if config.get("cryostat", "driver").strip().lower() != "optidry250":
            raise ValueError("Unsupported cryostat driver: %s" % config.get("cryostat", "driver"))
        cryostat = CryoPasqal(config.get("cryostat", "port"))
        logger.info('%s Pascal_Cryo connected' % datetime.datetime.now())
    except Exception as e:
        cryostat = CryoDemo() # launch cryostat interface
        logger.error('%s Pascal Cryostat initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s CryoDemo connected' % datetime.datetime.now())
    devices['cryostat'] = cryostat

    # initialize SLM
    try:
        if not _enabled(config, "slm"):
            raise RuntimeError("disabled by site configuration")
        SLM = Slm(dict(config["slm"]))
        logger.info('%s SLM connected' % datetime.datetime.now())
    except Exception as e:
        SLM = SLMDemo()
        logger.error('%s SLM initialization failed at interface startup. Error type %s' % (datetime.datetime.now(),str(e)))
        logger.info('%s SLMDemo connected' % datetime.datetime.now())
    devices['SLM'] = SLM

    spectrometers = {}
    stresing_params = _camera_parameters(config, "stresing", "stresing_optics")
    pixis_params = _camera_parameters(config, "pixis", "pixis_optics")
    grating_params = {"Stresing": stresing_params, "Pixis": pixis_params}
    Monochrom = _load_monochromator(config, grating_params)
    devices['Monochrom'] = Monochrom

    if _enabled(config, "stresing"):
        try:
            camera = StresingCamera(stresing_params, config.get("stresing", "vendor_config"))
            camera.attach_to_monochromator(Monochrom)
            spectrometers['Stresing'] = camera
            logger.info('%s Stresing connected' % datetime.datetime.now())
        except Exception as e:
            logger.warning(f'Stresing failed: {e}')

    if _enabled(config, "pixis"):
        try:
            camera = Pixis(pixis_params)
            spectrometers['Pixis'] = camera
            camera.attach_to_monochromator(Monochrom)
            logger.info('%s Pixis connected' % datetime.datetime.now())
        except Exception as e:
            logger.warning(f'Pixis failed: {e}')

    if _enabled(config, "ocean"):
        try:
            from drivers.OceanSpectrometer import OceanSpectrometer
            ocean = OceanSpectrometer()
            ocean.start()
            spectrometers['Ocean'] = ocean
            logger.info('%s Ocean connected' % datetime.datetime.now())
        except Exception as e:
            logger.warning(f'Ocean failed: {e}')

    if _enabled(config, "demo"):
        try:
            demo = SpectrometerDemo()
            spectrometers['Demo'] = demo
            logger.info('%s Demo spectrometer loaded' % datetime.datetime.now())
        except Exception as e:
            logger.warning(f'Demo failed: {e}')

    priority = csv_values(config, "site", "spectrometer_priority")
    default_spec = next(
        (spectrometers[name] for name in priority if name in spectrometers),
        next(iter(spectrometers.values()), None),
    )

    # Only store *object* in devices
    devices['spectrometer'] = default_spec

    # Return both — object dicts only
    return devices, spectrometers
