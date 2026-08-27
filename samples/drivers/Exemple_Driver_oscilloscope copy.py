from pathlib import Path
import sys

########################################################################################################################
################    Oscilloscope  Keysight communication            ##############################################3##
######################################################################################################################

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "src"))
from configuration import load_site_config
from src.drivers.Oscilloscope_Keysight_DSOX1202A import OscilloscopeController


site_config = load_site_config()
OscilloscopeController = OscilloscopeController(site_config.get("oscilloscope", "ip_address"))
OscilloscopeController.initialisation()
