#############################################################
#############################################################
# This module hosts a class defining a single beam in Colbert

#############################################################
#############################################################
import numpy as np
from src.compute.calibration import Calibration
from scipy.constants import c
from scipy.signal import sawtooth
from src.compute import colbertoutils as co
from scipy.constants import pi

class Beam:
    def __init__(self,currentCalibration):
        """
        Instantiates a Beam object describing all properties of a single beam
        Input:
            currentCalibration: Calibration object corresponding to the current setup
        output:
            Beam Object           
        """
        self.beamVerticalDelimiters=None # Vertical position delimiter of beam on SLM in pixels
        self.optimalPhaseCoefficients=None
        self.currentPhaseCoefficients=None
        self.phaseGratingAmplitude=None
        self.phaseGratingPeriod=None
        self.compressionCarrierFreq=None
        self.delayCarrierFreq=None
        self.micaslope=None
        self.calibration=currentCalibration
        self.activeRegion=None

    def set_compressionCarrierWave(self,compCarrierWave):
        """
        Sets the wavelength around which the phase coefficients for compression are defined
        input:
            wavelength: Compression carrier wavelength in m
        """
        self.compressionCarrierFreq=co.waveToAngFreq(compCarrierWave)

    def get_compressionCarrierWave(self):
        """
        Gets the wavelength around which the phase coefficients for compression are defined
        output:
            wavelength: Compression carrier wavelength in m
        """
        return co.angFreqToWave(self.compressionCarrierFreq)
    
    def generate_1Dgrating(amplitude,period,phase,num):
        '''
            Generates a sawtooth pattern for Diffraction-based spatiotemporal pulse shaping
            input:
                amplitude: (float) number between 0 and 1 setting the amplitude of the grating to amplitude*2*pi
                period: period of the sawtooth pattern in units of pixels
                phase: phase to be imparted on the diffracted beam (see eq. 13 of Turner et al. Rev. Sci. Instr. 2011)
                num: the number of pixels in the sawtooth pattern  
        '''
        indices=np.arange(num)
        offset=phase/(2*pi)*period
        y=amplitude*sawtooth(2*pi*(indices-offset)/period,width=0) % 2*pi
        return y



