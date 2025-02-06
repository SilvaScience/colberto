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

        # set parameters
        self.amplitude = 5

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # load the GUI
        project_folder = os.getcwd()
        uic.loadUi(project_folder + r'\src\GUI\SLM_GUI.ui', self)

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'amplitude':
            self.parameter_dict['amplitude'] = value
            self.amplitude = value

