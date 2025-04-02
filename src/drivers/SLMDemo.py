"""
Created on Tue Feb  06 15:26:53 2025

@author: Mathieu Desmarais
Hardware class to control SLM. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""

import numpy as np
from PyQt5 import QtWidgets, QtCore, uic
from collections import defaultdict
import time
from pathlib import Path
import sys
import os


class SLMDemo(QtWidgets.QMainWindow):
    name = 'SLM'

    def __init__(self):
        super(SLMDemo, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['temperature']['val'] = 500
        self.parameter_display_dict['temperature']['unit'] = ' K'
        self.parameter_display_dict['temperature']['max'] = 10000
        self.parameter_display_dict['temperature']['read'] = True
        self.parameter_display_dict['amplitude']['val'] = 1
        self.parameter_display_dict['amplitude']['unit'] = ' V'
        self.parameter_display_dict['amplitude']['max'] = 1000
        self.parameter_display_dict['amplitude']['read'] = False
        self.parameter_display_dict['greyscale_val']['val'] = 0
        self.parameter_display_dict['greyscale_val']['unit'] = ' '
        self.parameter_display_dict['greyscale_val']['max'] = 255
        self.parameter_display_dict['greyscale_val']['read'] = False

        # set parameters
        self.amplitude = 5
        self.temperature = 300
        self.greyscale_val = 0

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # load the GUI
        project_folder = Path(__file__).parents[1].resolve()
        uic.loadUi(Path(project_folder,r'GUI/SLM_GUI.ui'), self)

        def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'amplitude':
            self.parameter_dict['amplitude'] = value
            self.amplitude = value
        elif parameter == 'temperature':
            self.parameter_dict['temperature'] = value
            self.temperature = value
        elif parameter == 'greyscale_val':
            self.parameter_dict['greyscale_val'] = value
            self.greyscale_val = value

    def parameter_slm(self):
        rgb=1
        bit=1
        height= 1200
        width = 8
        depth = 1920
        RGB   = ctypes.c_uint(rgb)
        isEightBitImage = ctypes.c_uint(bit)
        return height,width,depth,RGB,isEightBitImage

    def write_image(self, image):
        return 42

