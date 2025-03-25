# This module define a calibration class. 
# This class hosts functions, methods and attributes related to Colbert calibrations

import numpy as np
import src.compute.colbertoutils as co

class Calibration():

    def __init__(self,SLM):
        """
        This builds an instance of a Calibration object without loading a file.
        Input:
            SLM: an SLM object

        """
        self.SLM=SLM # SLM Hosts all parameters related to the SLM currently in use
        
        self.pixelToWavelength=None
        self.phaseToGrayscale=None
        
    def set_pixelToWavelength(self,polynomial):
        '''
        Sets the pixel to wavelength calibration polynomial
        input:
            - polynomial: (Polynomial object) a Numpy Power series polynomial relating a pixel index to a wavelength in m
        '''
        self.pixelToWavelength=polynomial
    def get_spectrumAtPixel(self,pixels,unit='wavelength'):
        '''
        Gets the spectral position of light associated with a pixel on the SLM
        input:
            - pixels: (nd.array) the horizontal pixel index on the SLM
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
        wavelength=self.pixelToWavelength(pixels)
        return conversionFunction[unit](wavelength)

    def user_input_assign_pixelnumber_to_wavelength(self,peak_pos):
        
        ''' This function allows a user to assign peak positions to a specific wavelength. 
            Useful for calibrating pixel number to wavelength for stresing camera. 
            
                Inputs: peak_pos: 1D array containing the pixel number of peaks found in a data 
                    
                Outputs: wavelength: 1D array of containing the user assigned wavelength '''
    
        self.wavelength = np.empty(np.shape(peak_pos))
            
        for i in range (len(peak_pos)):
            
            self.val = input("Input the wavelength value associated with Peak # = {}: ".format(peak_pos[i]))
            self.wavelength[i] = self.val
                
            #print(self.wavelength)
    
        return self.wavelength

    def spectral_camera_pixel2wavelength_calib(self,peak_pos,wave,degree,pixels):
        ''' This function fits inputted data to a polynomial function.  
            
                Inputs: peak_pos: 1D array containing the pixel number of peaks found in a data 
                        wave: 1D array containing the wavelength of peak
                        degree: degree of polynomial fitting 
                            #3 should be fine for this calibration
                        pixels: array of pixel numbers (size = 1024)
                    
                Outputs: calibrated wavelength array'''
    
        self.fit_vals = np.polyfit(peak_pos,wave,degree)
        self.f = np.poly1d(self.fit_vals)

        self.wavelength_calib = self.f(pixels)
            
            
        return self.wavelength_calib
        
