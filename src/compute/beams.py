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
from numpy.polynomial import Polynomial as P
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
        self.optimalPhasePolynomial=None
        self.currentPhasePolynomial=None
        self.phaseGratingAmplitude=None
        self.phaseGratingPeriod=None
        self.compressionCarrierFreq=None#stored internally in angular frequency
        self.delayCarrierFreq=None
        self.calibration=currentCalibration
        self.beamHorizontalDelimiters=[0,self.calibration.SLM.get_size()[0]]
        self.beamVerticalDelimiters=None # Vertical position delimiter of beam on SLM in pixels. Default is whole SLM
        self.phaseGratingAmplitudeMask=np.ones(self.beamHorizontalDelimiters[1])
        self.maskOn=False #Is the mask enabled in the output grating?

    def set_beamVerticalDelimiters(self,delimiters):
        '''
            Sets the vertical delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        self.beamVerticalDelimiters=delimiters

    def set_beamHorizontalDelimiters(self,delimiters):
        '''
            Sets the horizontal delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        self.beamHorizontalDelimiters=delimiters

    def set_compressionCarrierWave(self,compCarrierWave):
        """
        Sets the wavelength around which the phase coefficients for compression are defined
        input:
            wavelength: Compression carrier wavelength in m
        """
        self.compressionCarrierFreq=co.waveToAngFreq(compCarrierWave)

    def get_compressionCarrier(self,unit='ang_frequency'):
        """
        Gets the wavelength around which the phase coefficients for compression are defined
        input:
            - unit: the unit in which to return the compression carrier frequency 
                - 'wavelength' : Returns in units of wavelength (m)
                - 'frequency' : Returns in units of frequency (Hz)
                - 'ang_frequency' (default): Returns in units of angular frequency (rad.Hz)
                - 'energy' : Returns in units of energy (eV)
        output:
            float: Compression carrier in specified units
        """
        conversionFunction={'wavelength':co.angFreqToWave,
                            'frequency':co.angFreqToFreq,
                            'ang_frequency': lambda x: x,
                            'energy':co.angFreqToeV}
        return conversionFunction[unit](self.compressionCarrierFreq)
    
    def set_optimalPhase(self,phasePolynomial,unit='fs'):
        '''
            Sets the optimal phase for the beam (spectral phase profile to apply to get best compression and synchronization with the LO)
            input:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
                - unit (str, default 'fs'): The units in which the phase coefficients are provided. 
        '''
        if unit=='fs':
            phasePolynomial=self.convertPhaseCoeffUnits(phasePolynomial)
        self.optimalPhasePolynomial=phasePolynomial

    def get_optimalPhase(self,indices):
        '''
            Gets the optimal phase for the beam (spectral phase profile to apply to get best compression and synchronization with the LO)
            output:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
        '''
        return self.optimalPhasePolynomial

    def set_currentPhase(self,phasePolynomial,mode='relative',unit='fs'):
        '''
            Sets the beam's phase profile 
            input:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
                - mode (string): Specifies if the phase is relative to the optimal phase profile ('relative', default) or absolute ('absolute')
        '''
        if unit=='fs':
            phasePolynomial=self.convertPhaseCoeffUnits(phasePolynomial)
        if mode=='relative':
            self.currentPhasePolynomial=self.optimalPhasePolynomial+phasePolynomial
        elif mode=='absolute':
            self.currentPhasePolynomial=phasePolynomial
    
    def get_currentPhase(self,mode='absolute'):
        '''
            Sets the beam's phase profile 
            input:
                - indices (nd.array of int) : Indices at which to sample the 
                - mode (string): Specifies if the phase returned is relative to the optimal phase profile ('relative', default) or absolute ('absolute')
            output:
                - (Numpy Polynomial): The current relative or absolute spectral phase taking arguments in angular frequency (rad.Hz)
        '''
        if mode=='relative':
            return self.currentPhasePolynomial-self.optimalPhasePolynomial
        elif mode=='absolute':
            return self.currentPhasePolynomial
    def get_horizontalIndices(self):
        '''
            Returns an array with indices from to 0 to the width of the SLM
            output:
                - nd.array (int): indices of the SLM's columns
        '''
        return np.arange(self.calibration.SLM.get_size()[0])

    def get_sampledCurrentPhase(self,indices=None):
        '''
            Returns the current phase at the horizontal pixel indices provided
            input:
                - indices (nd.array of int): (default none) the pixel indices at which to sample the optimal phase profile
                    By default, the phase is sampled at every column of the SLM
            output:
                -  nd.array of float: the current phase at the provided pixel column indices (in rad)
        
        '''
        if indices is None:
            indices=self.get_horizontalIndices()
        angFreq=self.calibration.get_spectrumAtPixel(indices,unit='ang_frequency')-self.get_compressionCarrier()
        return self.currentPhasePolynomial(angFreq)


    def get_optimalPhase(self):
        '''
            Gets the optimal phase for the beam (spectral phase profile to apply to get best compression and synchronization with the LO)
            output:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
        '''
        return self.optimalPhasePolynomial

    def get_sampledOptimalPhase(self,indices):
        '''
            Returns the optimal phase at the horizontal pixel indices provided
            input:
                - indices (nd.array of int): the pixel indices at which to sample the optimal phase profile
            output:
                -  nd.array of float: the optimal phase at the provided pixel column indices (in rad)
        
        '''
        angFreq=self.calibration.get_spectrumAtPixel(indices,unit='ang_frequency')-self.get_compressionCarrier()
        return self.optimalPhasePolynomial(angFreq)
    
    def set_gratingAmplitudeMask(self, mask):
        '''
            Sets the amplitude modulation along the horizontal axis of the phase grating.
            input:
                - mask (1d.array): The modulation of the grating's amplitude at a given pixel index from 0 (totally off) to 1 (fully on). The mask length must match the number of columns on the SLM's.
        '''
        if mask.shape[0]==self.get_horizontalIndices().shape[0]:
            self.phaseGratingAmplitudeMask=mask
        else:
            raise(IndexError("The mask length must match the number of columns on the SLM's."))
    def set_maskStatus(self,maskOn):
        '''
            Sets wether the mask should be applied or not.
            input:
                - maskOn (bool): Mask is applied to the phase grating when set to True and not applied when set to False
        '''
        self.maskOn=maskOn


    def set_gratingAmplitude(self,amplitude):
        '''
            Sets the amplitude of the grating in multiples of 2*pi
            input:
                - amplitude (float): The amplitude of the phase grating in units of 2*pi
        '''
        self.phaseGratingAmplitude=amplitude

    def get_gratingAmplitude(self):
        '''
            Gets the amplitude of the grating in multiples of 2*pi
            output:
                -(float): The amplitude of the phase grating in units of 2*pi
        '''
        return self.phaseGratingAmplitude

    def set_gratingPeriod(self,period):
        '''
            Sets the period of the grating in units of pixels
            input:
                - period (int): The period of the phase grating in units of pixels 
        '''
        self.phaseGratingPeriod=int(period)

    def get_gratingPeriod(self):
        '''
            Gets the period of the grating in units of pixels
            output:
                -(int): The period of the phase grating in units of pixels 
        '''
        return self.phaseGratingPeriod

    def makeGrating(self):
        '''
            Makes the phase grating using the current phase, amplitude and period
            output:
                - 2d.array: A 2D phase array corresponding to the current phase profile in rad
        '''
        phaseGratingImage=[]
        numberVerticalPixels=self.beamVerticalDelimiters[1]-self.beamVerticalDelimiters[0]
        phaseProfile=self.get_sampledCurrentPhase()
        for mask,phase in zip(self.phaseGratingAmplitudeMask,phaseProfile):
            row=self.generate_1Dgrating(self.get_gratingAmplitude(),self.get_gratingPeriod(),phase,num=numberVerticalPixels)
            if self.maskOn:
                row=mask*row
            phaseGratingImage.append(row)
        phaseGratingImage=np.array(phaseGratingImage)
        return phaseGratingImage 

    @staticmethod 
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
    @staticmethod
    def convertPhaseCoeffUnits(phasePolynomial,unit='fs'):
        '''
            Converts phase profile coefficient units from powers of selected unit to powers of s
            input:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
                - unit (str, default is 'fs'): The unit in which the coefficient
            '''
        if unit=='fs':
            unitConversionCoeff=[1e-15**n for n in range(len(phasePolynomial.coef))]
            phasePolynomial.coef=phasePolynomial.coef*unitConversionCoeff
        return phasePolynomial




