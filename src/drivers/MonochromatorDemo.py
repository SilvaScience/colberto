""" 
Author: david  
Date: 2025-02-13
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time


class MonochromatorDemo(QtCore.QThread):

    name = 'DemoMonochromator'
    type = 'Monochromator'

    def __init__(self):
        super(MonochromatorDemo, self).__init__()


        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['center_wl']['val'] = 500
        self.parameter_display_dict['center_wl']['unit'] = ' nm'
        self.parameter_display_dict['center_wl']['max'] = 1000
        self.parameter_display_dict['center_wl']['read'] = False

        # Parameters. Defines parameters that are required for by the interface
        self.center_wl = self.parameter_display_dict['center_wl']['val']

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        if parameter == 'center_wl':
            self.parameter_dict['center_wl']['val'] = value
            self.center_wl = value
        

