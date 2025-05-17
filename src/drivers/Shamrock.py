
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: KatieKoch, Felix Thouin
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time


class Shamrock(QtCore.QThread):
    
    name = 'Shamrock'
    type = 'Monochromator'
    
    def __init__(self,hardware_params):
        super(Shamrock, self).__init__()
        # This is the hardware parameters dictionnary. It is provided by hardware-specific configurations and are not changed in operation
        self.hardware_params=hardware_params
        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        
        self.parameter_display_dict = defaultdict(dict)
        
        self.parameter_dict['central_wave'] = 499.99
        self.parameter_dict['grating'] = 0
        
        self.parameter_display_dict['central_wave']['val'] = 000.00
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['max'] = 1000.00
        self.parameter_display_dict['central_wave']['read'] = False
        
        self.parameter_display_dict['grating']['val'] = 0
        self.parameter_display_dict['grating']['unit'] = ' grating choice'
        self.parameter_display_dict['grating']['max'] = 0
        self.parameter_display_dict['grating']['read'] = False

        self.grating_dispersions={0:150}
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

    def get_hardware_parameters(self):
        """
            Returns the hardware parameters of the monochromator
            output:
                - hardware_parameters (dict): A dictionnary of all hardware parameters including:
                    - f
                    - delta
                    - gamma
                    - n0
                    - offset_adjust
                    - d_grating
                    - x_pixel
                    - curvature

        """
        return self.hardware_params
    def get_monochromator_parameters(self):
        """
            Returns the current parameters of the monochromator.
            output:
                - central_wavelength (np.float): the central wavelength in nm
                - grating_lines_per_mm (np.float): the number of groove per mm of the selected grating
        """
        return self.central_wave, self.grating_dispersions[self.grating]


