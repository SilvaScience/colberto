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
import logging
import datetime
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))

logger = logging.getLogger(__name__)

class Measure_LUT_PhasetoGreyscale(QtCore.QThread):

    ''' 
        Runs a measurement that will scan through the greyscale values on half of the SLM display, 
        while keeping the other half set to zero and records the intensity on a spectrometer.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, spectra_number, scan_number):
        '''
         Initializes the LUT file measurement
         input:
             - devices: the devices dictionary holding at least a spectrometer and a SLM
             - parameters: 
        ''' 
        
        super(Measure_LUT_PhasetoGreyscale, self).__init__()

        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        # self.int_time = int_time
        self.spectra_number = spectra_number
        self.scan_number = scan_number
        self.GreyScale_Vals = np.arange(0,256,1) #255
        #self.GreyScale_Vals = np.arange(0, 11, 1)  # for testing purposes
        self.spectra = []  # preallocate spec array
        self.summedspec = []
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True

        self.parameter = parameter

    def run(self):
        logger.info('%s Run LUT File Calibration Measurement' % datetime.datetime.now())
        #print(time.strftime('%H:%M:%S') + ' Run LUT File Calibration Measurement')
        progress = 0
        for i in range(self.scan_number):
            self.sendProgress.emit(progress)
            for n in range(len(self.GreyScale_Vals)):
                #print(self.GreyScale_Vals[n])
                if not self.terminate:  # check whether stopping measurement is called
                    self.sendParameter.emit('greyscale_val', self.GreyScale_Vals[n])
                    # self.sendParameter.emit('int_time', self.int_time)

                    image = self.generate_calibibration_image(n)  # Generate Image for SLM

                    self.SLM.write_image(image, imagetype='raw')
                    #time.sleep(0.001)
                    logger.info(f'%s Image Sent n={n} {datetime.datetime.now()}')

                    #time.sleep(0.5)

                    # Acquire Data
                    self.summedspec = np.array(self.spectrometer.get_intensities())
                    for m in range(self.spectra_number-1):  # might need to make this (self.spectra_number-1)
                        logger.info(f'%s Spectra #{m} Acquired {datetime.datetime.now()}')
                        progress = (((n + 1) + (i * len(self.GreyScale_Vals))) / (
                                        len(self.GreyScale_Vals) * self.scan_number)) * 100

                        self.wls = np.array(self.spectrometer.get_wavelength())
                        self.spec = np.array(self.spectrometer.get_intensities())

                        self.summedspec = self.summedspec + self.spec
                        self.sendProgress.emit(progress)

                    self.spec = self.summedspec / self.spectra_number
                    #print('number of spectra', self.spectra_number)
                    self.sendSpectrum.emit(self.wls, self.spec)

                    logger.info(f'%s Spectrum Acquired for n={n} {datetime.datetime.now()}')


        self.sendProgress.emit(100)
        logger.info('%s LUT File Calibration Measurement Finished ' % datetime.datetime.now())
        #print(time.strftime('%H:%M:%S') + ' LUT File Calibration Measurement Finished')


    def generate_calibibration_image(self, right_val):
        """
        Generates an image (heigt,width) in grey value. The image is spit vertically in 2.

        - right_val : intensity (0-255) for right

        Return :
            np.ndarray of shape (height, width) dtype uint8
        """
        height, width, depth, RGB, isEightBitImage = self.SLM.get_parameters()
        left_val = 0

        img = np.zeros((height, width), dtype=np.uint8)
        middle = width // 2

        img[:, :middle] = left_val
        img[:, middle:] = right_val

        return img


    def stop(self):
        self.terminate = True
        logger.info('%s Request Stop ' % datetime.datetime.now())
