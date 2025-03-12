from pathlib import Path
import sys

########################################################################################################################
################    Oscilloscope  Keysight communication            ##############################################3##
######################################################################################################################

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.drivers.Oscilloscope_Keysight_DSOX1202A import OscilloscopeController



OscilloscopeController=OscilloscopeController()
OscilloscopeController.initialisation()