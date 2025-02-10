#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 09:45:58 2025

@author: katiekoch
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time


class MonochromDemo(QtCore.QThread):
    
    name = 'MonochromDemo'
    
    def __init__(self):
        super(MonochromDemo, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        
        self.parameter_display_dict = defaultdict(dict)
        
        self.parameter_dict['central_wave'] = 499.99
        self.parameter_dict['grating'] = 1
        
        self.parameter_display_dict['central_wave']['val'] = 000.00
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['max'] = 1000.00
        self.parameter_display_dict['central_wave']['read'] = False
        
        self.parameter_display_dict['grating']['val'] = 0
        self.parameter_display_dict['grating']['unit'] = ' grating choice'
        self.parameter_display_dict['grating']['max'] = 2
        self.parameter_display_dict['grating']['read'] = False
        
        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']
   
    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'central_wave':
            self.parameter_dict['central_wave'] = value
            self.central_wave = value
        elif parameter == 'grating':
            self.parameter_dict['grating'] = value
            self.grating = value


