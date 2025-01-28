# -*- coding: utf-8 -*-
"""
Created on Thu Sep  4 13:26:53 2022

@author: NanoUltrafast2
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

import requests
import numpy as np
import json
from PyQt5 import QtCore
import time
from collections import defaultdict
import time


class SpectrometerDemo(QtCore.QThread):

    name = 'Spectrometer'
    
    def __init__(self):
        super(SpectrometerDemo, self).__init__()

        # parameters
        self.speclength = 2048

        # set parameter dict
        self.parameter_dict = defaultdict()
        
        # setting up variables, open array
        self.spectrum = np.array([])
        self.wavelength = np.array([])
        self.stop = False
        self.parameter_dict['int_time'] = 500
        self.parameter_dict['binning'] = 1
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['int_time']['val'] = 500
        self.parameter_display_dict['int_time']['unit'] = ' ms'
        self.parameter_display_dict['int_time']['max'] = 10000
        self.parameter_display_dict['int_time']['read'] = False
        self.parameter_display_dict['binning']['val'] = 1
        self.parameter_display_dict['binning']['unit'] = ' px'
        self.parameter_display_dict['binning']['max'] = 1000
        self.parameter_display_dict['binning']['read'] = False

    def set_parameter(self,parameter,value):
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
        elif parameter == 'binning':
            pass
              
    def acquire(self):
        self.spectrum = self.getIntensities()

    def getWavelength(self):
        return np.linspace(177.2218, 884.00732139, 2048)

    def getIntensities(self):
        # create random spectrum
        t1 = time.time()
        wls = np.linspace(177.2218, 884.00732139, 2048)
        sigma = 40
        mu = 2
        xc = 620.
        spec = (0.8+0.2*np.random.rand(1))*(np.random.randint(0, 50, 2048) + self.parameter_dict['int_time']*2000. / (sigma * np.sqrt(2. * np.pi)) * np.exp(
            - (wls - mu - xc) ** 2. / (2. * sigma ** 2.)) - 50),
        flatspec = np.array(spec)
        time.sleep(self.parameter_dict['int_time']/1000)
        if time.time()-t1 >0.1:
            time.sleep(0.1)
        return flatspec.reshape(-1)

