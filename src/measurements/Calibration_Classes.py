#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  5 13:47:39 2025

@author: katiekoch
"""

''' Calibration Classes'''

import time
from PyQt5 import QtCore
import numpy as np
from pathlib import Path
import sys
from ctypes import *
import h5py
import scipy.signal as signal
from PyQt5.QtWidgets import QApplication, QFileDialog
import csv
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration

from src.drivers.Slm_Meadowlark_optics import SLM
from src.drivers.Slm_Meadowlark_optics import ImageGen

class Measure_LUT_PhasetoGreyscale(QtCore.QThread):

    ''' 
        Runs a measurement that will scan through the greyscale values on half of the SLM display, 
        while keeping the other half set to zero and records the intensity on a spectrometer.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, int_time, spectra_number, scan_number):
        '''
         Initializes the LUT file measurement
         input:
             - devices: the devices dictionary holding at least a spectrometer and a SLM
             - parameters: 
        ''' 
        
        super(Measure_LUT_PhasetoGreyscale, self).__init__()

        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.ImageGen = devices['ImageGen']
        self.int_time = int_time
        self.spectra_number = spectra_number
        self.scan_number = scan_number
        self.GreyScale_Vals = np.arange(0,256,1) #255
        #print(self.GreyScale_Vals)
        #print(len(self.GreyScale_Vals))
        #self.GreyScale_Vals = np.arange(0, 11, 1)  # for testing purposes
        self.spectra = []  # preallocate spec array
        self.summedspec = []
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True

        self.parameter = parameter

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run LUT File Calibration Measurement')
        progress = 0
        for i in range(self.scan_number):
            self.sendProgress.emit(progress)
            for n in range(len(self.GreyScale_Vals)):
                #print(self.GreyScale_Vals[n])
                if not self.terminate:  # check whether stopping measurement is called
                    self.sendParameter.emit('greyscale_val', self.GreyScale_Vals[n])
                    self.sendParameter.emit('int_time', self.int_time)

                    image = self.create_SLM_image(n) #Generate Image for SLM

                    self.SLM.write_image(image) #send image to SLM
                    time.sleep(self.int_time / 1000 + 0.05)

                    # Acquire Data
                    for m in range(self.spectra_number):  # might need to make this (self.spectra_number-1)
                        self.summedspec = np.array(self.spectrometer.get_intensities())
                        progress = (((n + 1) + (i * len(self.GreyScale_Vals))) / (
                                        len(self.GreyScale_Vals) * self.scan_number)) * 100

                        self.wls = np.array(self.spectrometer.get_wavelength())
                        self.spec = np.array(self.spectrometer.get_intensities())

                        self.summedspec = self.summedspec + self.spec
                        self.sendProgress.emit(progress)

                    self.spec = self.summedspec / self.spectra_number
                    self.sendSpectrum.emit(self.wls, self.spec)
                    print(time.strftime('%H:%M:%S') + ' Spectrum acquired')

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' LUT Calibration Finished')

    def create_SLM_image(self, pixel_val_one):
        height ,width, depth, RGB, isEightBitImage = self.SLM.parameter_slm()
        
        image = np.zeros((height, width,8),dtype=np.uint8)
        wfc = np.zeros((height, width,8),dtype=np.uint8)
        
        RGB = 0
        pixels_per_stripe = int(width/2) #pixels per stripe
        pixel_value_one = pixel_val_one  # reference value.
        pixel_value_two = 0 # reference value. 
        vertical = True # vertical or horizontal stripes
        
        self.ImageGen.generate_stripe(image.ctypes.data_as(POINTER(c_ubyte)), wfc.ctypes.data_as(POINTER(c_ubyte)),
                              width, height, depth, pixel_value_one , pixel_value_two, pixels_per_stripe, vertical, RGB)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
########################################################################################################################

class Generate_LUT_PhasetoGreyscale(QtCore.QThread):

        '''
            Analyze measured spectrum & generate a Phase2GreyScale LUT file.
        '''

        sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
        sendProgress = QtCore.pyqtSignal(float)
        sendParameter = QtCore.pyqtSignal(str, float)

        def __init__(self, devices, parameter, filepath):
            '''
             Initializes the LUT File Calculations
             input:
                 - devices: the devices dictionary holding at least a spectrometer and a SLM
                 - parameters:
                 - filepath: path where the measured spectra is stored
            '''

            super(Generate_LUT_PhasetoGreyscale, self).__init__()

            self.filepath = filepath
            self.terminate = False
            self.acquire_measurement = True

        def run(self):
            print(time.strftime('%H:%M:%S') + ' Run LUT File Generation')
            progress = 0

            fn = self.filepath
            print(fn)
            with h5py.File(fn, 'r') as hdf: #analyze data file loaded
                data = hdf.get('spectra')
                data_set = np.array(data)
                print(data_set.shape)

                grp = hdf['spectra']
                # print(grp.attrs['parameter_keys'])
                params = grp.attrs['parameter_keys']
                wave = grp.attrs['yaxis']

            try:
                index = np.where(params == 'greyscale_val')
                index = np.array(index)
                idx_val = int(index[0])
                print("String found at index", index)
            except ValueError:
                print("String not found!")

            Total_GreyScale_Vals = data_set[idx_val, :]
            #print(Total_GreyScale_Vals)
            Uniq_GreyScale_Vals = np.unique(Total_GreyScale_Vals)

            cut = len(params)
            spectra = data_set[cut:, :] #trim data set to include only measured spectra

            avg_spectrum = np.zeros((len(wave), len(Uniq_GreyScale_Vals))) #set array size to average spectrum from diff scans
            for j in range(len(Uniq_GreyScale_Vals)):
                for i in range(len(Total_GreyScale_Vals)):
                    if Total_GreyScale_Vals[i] == Uniq_GreyScale_Vals[j]:
                        avg_spectrum[:, j] = avg_spectrum[:, j] + spectra[:, i]

            scan_num = len(Total_GreyScale_Vals) / len(Uniq_GreyScale_Vals)
            #print(Total_GreyScale_Vals)
            print(len(Total_GreyScale_Vals))
            #print(Uniq_GreyScale_Vals)
            print(len(Uniq_GreyScale_Vals))

            print(scan_num)

            avg_spectrum = avg_spectrum / scan_num
            print('Spectrum Averaged')

            wavelength_shift = np.zeros((len(wave),len(Uniq_GreyScale_Vals)))#creating the right size array
            phase_shift = np.zeros((len(wave),len(Uniq_GreyScale_Vals)))#creating the right size array

            #function to determine phse shifts utilizing a fourier transform
            for i in range(len(Uniq_GreyScale_Vals)):
                wavelength_shift[:, i], phase_shift[:, i] = self.detect_peak_shift(wave, avg_spectrum[:,0], avg_spectrum[:, i])
            print('Phase Shift Calculated')

            self.generate_phase_greyscale_LUT(wave, phase_shift, Uniq_GreyScale_Vals)

            self.sendProgress.emit(100)
            print(time.strftime('%H:%M:%S') + ' LUT File Generation Finished')


        def detect_peak_shift(self, wavelengths, ref_spec, shift_spec):
            """
               Detects the peak shift between a reference spectrum and a test spectrum.
               Returns the wavelength shift and phase shift in radians.

               Parameters:
                   wavelengths (array): The spectrum wavelengths.
                   reference_spec (array): The baseline spectrum.
                   shift_spec (array): The shifted spectrum (with greyscale applied).

               Returns:
                   wavelength_shift (float): The shift in wavelength units.
                   phase_shift (float): The phase shift in radians.
               """

            # Cross-correlate the signals to find the shift
            correlation = signal.correlate(shift_spec, ref_spec, mode='full')
            shift_index = np.argmax(correlation) - (len(ref_spec) - 1)
            wavelength_shift = wavelengths[shift_index] - wavelengths[0]

            # Compute the phase shift using Fourier Transform
            fft_ref = np.fft.fft(ref_spec)
            fft_test = np.fft.fft(shift_spec)

            # Phase difference calculation
            phase_diff = np.angle(fft_test) - np.angle(fft_ref)
            phase_shift = np.mean(phase_diff)  # Average phase shift

            return wavelength_shift, phase_shift

        def generate_phase_greyscale_LUT(self, wave, phase_shift_array, greyscale_values):
            """
            Generates a phase-to-greyscale Look-Up Table (LUT) based on the detected phase shifts and allows the user to choose a save location using Qt.

            Parameters:
                phase_shift_array (array): The array of phase shifts at different frequencies.
                greyscale_vales (array): The array with the greyscale values applied to the SLM pattern.
            """

            output_file, _ = QFileDialog.getSaveFileName(None, "Save LUT File", "", "CSV Files (*.csv)")

            if output_file:
                with open(output_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    header = ["Wavelength"] + [f"Greyscale {int(g)}" for g in greyscale_values]
                    writer.writerow(header)

                    print(wave.shape)

                    for i in range(phase_shift_array.shape[0]):
                        writer.writerow([wave[i]] + list(phase_shift_array[i, :]))
                print(f"LUT file saved to: {output_file}")
            else:
                print("LUT file save canceled.")

        def stop(self):
            self.terminate = True
            print(time.strftime('%H:%M:%S') + ' Request Stop')


