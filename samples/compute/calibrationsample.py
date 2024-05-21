
from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM 
from numpy.polynomial import Polynomial as P
import numpy as np

slm=SLM(600,300)
print('Widht: %d and heigth %d of SLM '%(slm.width,slm.height))
cal=Calibration(slm)
pix2wave=P(1e-9*np.array([500,1/6]))
cal.set_pixelToWavelength(pix2wave)
print(cal.get_spectrumAtPixel(np.arange(slm.getSize()[0])))
print(cal.get_spectrumAtPixel(np.arange(slm.getSize()[0]),unit='frequency'))
print(cal.get_spectrumAtPixel(np.arange(slm.getSize()[0]),unit='ang_frequency'))
print(cal.get_spectrumAtPixel(np.arange(slm.getSize()[0]),unit='energy'))
