# This module define a calibration class. 
# This class hosts functions, methods and attributes related to Colbert calibrations

import numpy as np
import src.compute.colbertoutils as co

from scipy.signal import find_peaks
import datetime

import tkinter as tk
from tkinter import filedialog

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

    def peak_finder(self,Data,height):
    
        ''' This function takes a 1-D array and finds all local maxima by simple comparison of neighboring values. 
                Inputs: Data - signal with peaks 
                        Height: required height of peaks
                    
                Outputs: peaks: 1D array with x-positon of peaks that satisfy given conditions
                         peaks_heights: 1D array with the heights of peaks found'''
            
        self.peaks,self.params = find_peaks(Data,height=height)
  
        self.peak_pos = self.peaks
        #print(self.peak_pos)
    
        self.peak_heights = self.params["peak_heights"]
        #print(self.peak_heights)
    
        return self.peak_pos, self.peak_heights

    def user_input_assign_pixelnumber_to_wavelength(self,peak_pos):
        
        ''' This function allows a user to assign peak positions to a specific wavelength. 
            Useful for calibrating pixel number to wavelength for stresing camera. 
            
                Inputs: peak_pos: 1D array containing the pixel number of peaks found in a data 
                    
                Outputs: wavelength: 1D array of containing the user assigned wavelength '''
    
        self.wavelength = np.empty(np.shape(self.peak_pos))
            
        for i in range (len(self.peak_pos)):
            
            self.val = input("Input the wavelength value associated with Peak # = {}: ".format(self.peak_pos[i]))
            self.wavelength[i] = self.val
                
            #print(self.wavelength)
    
        return self.wavelength

    def stresing_pixel2wavelength_calib(self,peak_pos,wave,degree):
        ''' This function fits inputted data to a polynomial function.  
            
                Inputs: peak_pos: 1D array containing the pixel number of peaks found in a data 
                        wave: 1D array containing the wavelength of peak
                        degree: degree of polynomial fitting 
                            #3 should be fine for this calibration
                    
                Outputs: calibrated wavelength array'''
    
        self.fit_vals = np.polyfit(self.peak_pos,self.wave,self.degree)
        self.f = np.poly1d(self.fit_vals)

        self.wavelength_calib = self.f(self.pixels)
            
            
        return self.wavelength_calib


    def save_data(self,filename, Data):
        
        ''' Saves data to a user defined path.
                Inputs: filename: label the file as you want 
                            #the program will add date & time to the end of this name 
                        Data: array that you want to save
                    
                Outputs: '''
    
        self.folder_path = filedialog.askdirectory()
        self.time = datetime.datetime.now()

        self.filename_with_datetime = self.filename + '_' + str(self.time.year) + '_' + str(self.time.month) + '_' + str(self.time.day) + '_' + str(self.time.hour) + '_' + str(self.time.minute) + '_' + str(self.time.second)
        #print(self.filename_with_date)

        self.filepath = self.folder_path + '/' + self.filename_with_datetime
        #print(self.filepath)
    
        np.savetxt(self.filepath +'.txt', self.Data)
    
        print('Data saved as: ' + self.filepath)
    
        return
        
