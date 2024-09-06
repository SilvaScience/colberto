#### This modules hosts all general purpose functions for Colbert
from scipy.constants import c,h,pi,e

from scipy.signal import find_peaks
import datetime

import tkinter as tk
from tkinter import filedialog

import numpy as np

def waveToeV(wave):
    """
    Converts vacuum wavelengths (m) to energy in eV
    """ 
    return h*c/wave/e

def waveToFreq(wave):
    """
    Converts vacuum wavelengths (m) to frequency in Hz
    """ 
    return c/wave

def waveToAngFreq(wave):
    """
    Converts vacuum wavelengths (m) to angular frequency in rad.Hz
    """ 
    return 2*pi*c/wave

def angFreqToWave(angFreq):
    """
    Converts angular frequency in rad.Hz to vacuum wavelengths (m)
    """ 
    return 2*pi*c/angFreq

def angFreqToFreq(angFreq):
    """
    Converts angular frequency in rad.Hz to frequency (Hz)
    """ 
    return waveToFreq(angFreqToWave(angFreq))

def angFreqToeV(angFreq):
    """
    Converts angular frequency in rad.Hz to frequency (Hz)
    """ 
    return waveToeV(angFreqToWave(angFreq))


def peak_finder(Data,height):
    ''' This function takes a 1-D array and finds all local maxima by simple comparison of neighboring values. 
            Inputs: Data - signal with peaks 
                    Height: required height of peaks
            Outputs: peaks: 1D array with x-positon of peaks that satisfy given conditions
                     peaks_heights: 1D array with the heights of peaks found'''
            
    peaks,params = find_peaks(Data,height=height)
  
    peak_pos = peaks
    #print(peak_pos)
    
    peak_heights = params["peak_heights"]
    #print(peak_heights)
    
    return peak_pos, peak_heights

def save_data(filename, Data):
    ''' Saves data to a user defined path.
            Inputs: filename: label the file as you want 
                        #the program will add date & time to the end of this name 
                    Data: array that you want to save
                    
            Outputs: '''
    
    folder_path = filedialog.askdirectory()
    time = datetime.datetime.now()

    filename_with_datetime = filename + '_' + str(time.year) + '_' + str(time.month) + '_' + str(time.day) + '_' + str(time.hour) + '_' + str(time.minute) + '_' + str(time.second)
    #print(self.filename_with_date)

    filepath = folder_path + '/' + filename_with_datetime
    #print(filepath)
    
    np.savetxt(filepath +'.txt', Data)
    
    print('Data saved as: ' + filepath)
    
    return
