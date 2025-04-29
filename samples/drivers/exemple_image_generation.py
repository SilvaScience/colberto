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
    bm=Beam(1200,1920)
    bm.set_pixelToWavelength(P(1e-9*np.array([500,1/6])))# Sets bogus polynomial for pix to wave conversionpix2wave
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

def normalize_phase_image(image, max_phase=2 * np.pi):
    """
    Convert a float64 phase image (0 to 2π) to uint8 (0 to 255).
    """
    image = np.clip(image, 0, max_phase)  # safety
    norm_img = (image / max_phase) * 255
    return norm_img.astype(np.uint8)

if __name__=="__main__":
    image=beam_image_gen()
    plt.figure()
    plt.imshow(image)
    plt.figure()
    int8image=normalize_phase_image(image)
    plt.imshow(int8image)
    plt.show()


