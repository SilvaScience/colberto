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
import logging

logger = logging.getLogger(__name__)

class Beam:
    def __init__(self,SLMWidth,SLMHeight):
        """
        Instantiates a Beam object describing all properties of a single beam. All phase are in rad (units of 2*pi)
        Input:
            currentCalibration: Calibration object corresponding to the current setup
        output:
            Beam Object           
        """
        self.SLMWidth=SLMWidth
        self.SLMHeight=SLMHeight
        self.beamOn=True
        self.current_phase_mode='relative'
        # initilization of parameters to default benign values
        self.set_beamHorizontalDelimiters([0,SLMWidth])
        self.set_beamVerticalDelimiters([0,SLMHeight])
        self.make_mask()
        self.set_optimalPhase(P([0,0,0]))
        self.set_currentPhase(P([0,0,0]))
        self.phaseGratingAmplitude=1
        self.phaseGratingPeriod=None
        self.indices=self.get_horizontalIndices()
        self.set_compressionCarrierWave(600e-9)
        self.set_delayCarrierWave(600e-9)
        self.maskOn=True
        self.pixelToWavelength=P(1e-9*np.array([600,0.05]))

    def make_mask(self,horizontalDelimiters=None,verticalDelimiters=None):
        '''
            Makes an amplitude mask corresponding to the vertical and horizontal delimiters
            input:
                - horizontalDelimiters (nd.array, Default None) Indices of the two horizontal limiting edges of the beam. Default uses internal delimiters
                - verticalDelimiters (nd.array, Default None) Indices of the two vertical limiting edges of the beam. Default uses internal delimiters
        '''
        self.mask=np.zeros((self.SLMHeight,self.SLMWidth))
        if horizontalDelimiters is None:
            horizontalDelimiters=self.get_beamHorizontalDelimiters()
        if verticalDelimiters is None:
            verticalDelimiters=self.get_beamVerticalDelimiters()
        if self.beamOn:
            self.mask[verticalDelimiters[0]:verticalDelimiters[1],horizontalDelimiters[0]:horizontalDelimiters[1]]=1

    def get_mask(self):
        ''' 
            Returns the amplitude mask currently set and the wether it is on or not.
            input:
                None
            output:
                - nd.array: the amplitude mask currently configured
                - bool: True if the mask is applied to the beam
        '''
        return self.mask, self.maskOn
    
    def set_beamVerticalDelimiters(self,delimiters):
        '''
            Sets the vertical delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        self.beamVerticalDelimiters=delimiters

    def get_beamVerticalDelimiters(self):
        '''
            Returns the vertical delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        return self.beamVerticalDelimiters

    def get_beamHorizontalDelimiters(self):
        '''
            Returns the vertical delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        return self.beamHorizontalDelimiters


    def set_beamHorizontalDelimiters(self,delimiters):
        '''
            Sets the horizontal delimiters of the beam
            input:
                - delimiters (nd.array): A 1d 2 element array specifying the vertical beginning and end pixels of the beam (0 indexed) [beginning, end]
        '''
        self.beamHorizontalDelimiters=delimiters
        self.phaseGratingAmplitudeMask=np.ones(self.beamHorizontalDelimiters[1])

    def get_spectrumAtPixel(self,pixels=None,unit='wavelength'):
        '''
        Gets the spectral position of light associated with a pixel on the SLM
        input:
            - pixels: (nd.array) the horizontal pixel index on the SLM. By default, the phase is sampled at every column of the SLM 
            - unit: the unit in which to return the spectrum axis allows for
                - 'wavelength' (default): Returns in units of wavelength (m)
                - 'frequency' : Returns in units of frequency (Hz)
                - 'ang_frequency' : Returns in units of angular frequency (rad.Hz)
                - 'energy' : Returns in units of energy (eV)
        output: (nd.array) the spectral position associated with the pixels in pixels

        '''
        conversionFunction={'wavelength':lambda x: x,
                            'frequency':co.waveToFreq,
                            'ang_frequency':co.waveToAngFreq,
                            'energy':co.waveToeV}
        if pixels is None:
            pixels=self.indices
        wavelength=self.pixelToWavelength(pixels)
        return conversionFunction[unit](wavelength)

    def set_pixelToWavelength(self,polynomial):
        '''
        Sets the pixel to wavelength calibration polynomial for this beam
        input:
            - polynomial: (Polynomial object) a Numpy Power series polynomial relating a pixel index to a wavelength in m
        ''' 
        self.pixelToWavelength=polynomial

    def set_delayCarrierWave(self,compCarrierWave=None):
        """
        Sets the wavelength around which the phase coefficients for delay are defined
        input:
            wavelength: Compression carrier wavelength in m
        """
        self.delayCarrierFreq=co.waveToAngFreq(compCarrierWave)

    def get_delayCarrier(self,unit='ang_frequency'):
        """
        Gets the wavelength around which the phase coefficients for pulse delaying (rotating frame) are defined
        input:
            - unit: the unit in which to return the compression carrier frequency 
                - 'wavelength' : Returns in units of wavelength (m)
                - 'frequency' : Returns in units of frequency (Hz)
                - 'ang_frequency' (default): Returns in units of angular frequency (rad.Hz)
                - 'energy' : Returns in units of energy (eV)
        output:
            float: Delay carrier in specified units
        """
        conversionFunction={'wavelength':co.angFreqToWave,
                            'frequency':co.angFreqToFreq,
                            'ang_frequency': lambda x: x,
                            'energy':co.angFreqToeV}
        return conversionFunction[unit](self.delayCarrierFreq)

    def set_compressionCarrierWave(self,compCarrierWave=None):
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
        self.optimalPhasePolynomial=self.convertPhaseCoeffUnits(phasePolynomial,input_units=unit,output_units='s')

    def get_optimalPhase(self,units_to_return='s'):
        '''
            Sets the beam's phase profile 
            input:
                - indices (nd.array of int) : Indices at which to sample the 
                - units_to_return (str 'fs' or 's'): Specifies the units in which to return the polynomial. Polynomial is stored internally in units of seconds
                    Specifying 'fs' converts the internal units to be displayed in fs.
            output:
                - (Numpy Polynomial): The current relative or absolute spectral phase taking arguments in angular frequency (rad.Hz)
        '''
        return self.convertPhaseCoeffUnits(self.optimalPhasePolynomial,input_units='s',output_units=units_to_return)
    
    def set_current_phase_mode(self,mode):
        """
            Sets the current phase to be stored relatively (mode='relative') to the optimal phase coefficient or not (mode='absolute')
            input:
                - mode (str): 'relative' for the phase to be stored relatively to optimal phase or 'absolute' otherwise
        """
        if mode=='relative' or mode=='absolute':
            self.current_phase_mode=mode
        else:
            raise ValueError('Current phase mode must be a str (\'relative\' or \'absolute\')') 
    
    def get_current_phase_mode(self):
        """
            Returns the current phase reference mode
            output:
                - mode (str): 'relative' for the phase to be stored relatively to optimal phase or 'absolute' otherwise
        """
        return self.current_phase_mode
    
    def set_currentPhase_optimal(self):
        """
            Sets the current phase to match to optimal phase
        """
        self.set_currentPhase(self.optimalPhasePolynomial,mode='absolute',unit='s')

    def set_currentPhase(self,phasePolynomial,mode=None,unit='fs'):
        '''
            Sets the beam's phase profile 
            input:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
                - mode (string): Specifies if the phase is relative to the optimal phase profile ('relative', default) or absolute ('absolute')
        '''
        if mode is None:
            mode=self.current_phase_mode
        phasePolynomial=self.convertPhaseCoeffUnits(phasePolynomial,input_units=unit,output_units='s')
        if mode=='relative':
            self.currentPhasePolynomial=self.optimalPhasePolynomial+phasePolynomial
        elif mode=='absolute':
            self.currentPhasePolynomial=phasePolynomial
    
    def get_currentPhase(self,mode=None,units_to_return='s'):
        '''
            Sets the beam's phase profile 
            input:
                - indices (nd.array of int) : Indices at which to sample the 
                - mode (string): Specifies if the phase returned is relative to the optimal phase profile ('relative', default) or absolute ('absolute')
                - units_to_return (str 'fs' or 's'): Specifies the units in which to return the polynomial. Polynomial is stored internally in units of seconds
                    Specifying 'fs' converts the internal units to be displayed in fs.
                - for_display (bool): Specifies if the phase polynomial coeff are to be used for display only. In this case, the value of the optimal phase polynomial is not subtracted.
            output:
                - (Numpy Polynomial): The current relative or absolute spectral phase taking arguments in angular frequency (rad.Hz)
        '''
        if mode is None:
            mode=self.current_phase_mode
        if mode=='relative':
            returnPolynomial=self.currentPhasePolynomial-self.optimalPhasePolynomial
        elif mode=='absolute':
            returnPolynomial=self.currentPhasePolynomial
        return self.convertPhaseCoeffUnits(returnPolynomial,input_units='s',output_units=units_to_return)
    def get_horizontalIndices(self):
        '''
            Returns an array with indices from the active part of the SLM
            output:
                - nd.array (int): indices of the SLM's columns
        '''
        return np.arange(self.beamHorizontalDelimiters[0],self.beamHorizontalDelimiters[1])

    def get_sampledCurrentPhase(self,indices=None,mode='absolute'):
        '''
            Returns the current phase at the horizontal pixel indices provided
            input:
                - indices (nd.array of int): (default none) the pixel indices at which to sample the optimal phase profile
                    By default, the phase is sampled at every column of the SLM
                - mode (string): Specifies if the phase returned is relative to the optimal phase profile ('relative', default) or absolute ('absolute')
            output:
                -  nd.array of float: the current phase at the provided pixel column indices (in rad)
        
        '''
        if indices is None:
            indices=self.indices
        phase_polynomial=self.get_currentPhase(mode=mode)
        compression_polynomial=phase_polynomial.copy()
        if len(phase_polynomial.coef)>1:
            delay_polynomial=P([0,phase_polynomial.coef[1]])
            compression_polynomial.coef[1]=0
        else:
            delay_polynomial=P([0,0])
        angFreq_compression=self.get_spectrumAtPixel(indices,unit='ang_frequency')-self.get_compressionCarrier()
        angFreq_delay=self.get_spectrumAtPixel(indices,unit='ang_frequency')-self.get_delayCarrier()
        return delay_polynomial(angFreq_delay)+compression_polynomial(angFreq_compression)

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
    
    def get_beamStatus(self):
        '''
            Returns wether the beam is on or not.
            output:
                - beamOn (bool): Beam is ON (non-zero phase grating) when set to True 
        '''
        return self.beamOn

    def set_beamStatus(self,beamOn):
        '''
            Sets wether the beam should be on or not.
            input:
                - beamOn (bool): Beam is ON (non-zero phase grating) when set to True 
        '''
        self.beamOn=beamOn

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
        self.make_mask()
        phaseGratingImage=np.zeros((self.SLMHeight,self.SLMWidth))
        if self.phaseGratingPeriod is None:
            return phaseGratingImage
        numberVerticalPixels=self.SLMHeight
        phaseProfile=self.get_sampledCurrentPhase()
        for i,phase in enumerate(phaseProfile):
            phaseGratingImage[:,i]=self.generate_1Dgrating(self.get_gratingAmplitude(),self.get_gratingPeriod(),phase,num=numberVerticalPixels)
        phaseGratingImage=np.array(phaseGratingImage)
        if self.maskOn:
            phaseGratingImage=phaseGratingImage*self.mask
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
    def convertPhaseCoeffUnits(phasePolynomial,input_units='fs',output_units='s'):
        '''
            Converts phase profile coefficient units from powers of selected unit to powers of s
            input:
                - phasePolynomial (numpy Polynomial object): A Numpy Polynomial representing the phase profile taking arguments in angular frequency (rad.Hz)
                - input_unit (str, default is 'fs'): The unit in which the coefficient are input
                - output_unit (str, default is 's'): The unit in which the output coefficients are desired
            '''
        new_phasePolynomial=phasePolynomial.copy()
        multiplier_in={'fs':1e-15,
                    's':1}
        multiplier_out={'fs':1e15,
                    's':1}
        new_phasePolynomial.coef=[coeff*(multiplier_in[input_units]*multiplier_out[output_units])**n for n,coeff in enumerate(phasePolynomial.coef)]
        return new_phasePolynomial




