
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
    
    def __init__(self, hardware_params, center_wavelength=650.0, grating_densities=(150.0,)):
        super(Shamrock, self).__init__()
        self.center_wl = float(center_wavelength)
        self.grating = 1
        self.grating_densities = np.asarray(grating_densities, dtype=float)
        self.num_gratings = len(self.grating_densities)

        # This is the hardware parameters dictionnary. It is provided by hardware-specific configurations and are not changed in operation
        self.hardware_params=hardware_params
        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        
        self.parameter_display_dict = defaultdict(dict)
        
        self.parameter_dict['central_wave'] = self.center_wl
        self.parameter_dict['grating'] = self.grating
        
        self.parameter_display_dict['central_wave']['val'] = self.center_wl
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['min'] = 200.00
        self.parameter_display_dict['central_wave']['max'] = 1100.00
        self.parameter_display_dict['central_wave']['read'] = False
        
        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grating choice'
        self.parameter_display_dict['grating']['max'] = self.num_gratings
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
            self.center_wl = value
        elif parameter == 'grating':
            self.parameter_dict['grating'] = value
            self.grating = value

    def get_hardware_parameters(self, name):
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
        return self.hardware_params[name]
    def get_monochromator_parameters(self):
        """
            Returns the current parameters of the monochromator.
            output:
                - central_wavelength (np.float): the central wavelength in nm
                - grating_lines_per_mm (np.float): the number of groove per mm of the selected grating
        """
        return self.center_wl, self.grating_densities[int(self.grating - 1)]

