from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM2 
from src.drivers.Slm_Meadowlark_optics import SLM
from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial as P
import numpy as np

'''
Exemple of image generation for the SLM. The idea is to create the image outside of SLMdemo to only import it in the code
'''
def beam_image_gen():
    slm=SLM()
        

    cal=Calibration(slm)# Initialize calibration with SLM object
    pix2wave=P(1e-9*np.array([500,1/6]))# Sets bogus polynomial for pix to wave conversion
    cal.set_pixelToWavelength(pix2wave)
    bm=Beam(cal)
    bm.set_compressionCarrierWave(532e-9)

    bm.set_optimalPhase(P([0,0,1000,500]))
    bm.set_currentPhase(P([0,100,500]),mode='relative')
    bm.set_beamVerticalDelimiters([0,1200])



    amplitude=1
    bm.set_gratingAmplitude(amplitude)
    period=100
    bm.set_gratingPeriod(period)

    image= bm.makeGrating()
    return image


