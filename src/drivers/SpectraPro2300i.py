
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: KatieKoch, Felix Thouin
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
import serial
import re
import logging
logger = logging.getLogger(__name__)

class SpectraPro2300i(QtCore.QThread):
    
    name = 'SpectraPro2300i'
    type = 'Monochromator'
    
    def __init__(self,hardware_params,port):
        super(SpectraPro2300i, self).__init__()

        # set up spectrograph
        self.serial_busy = False
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        numbers = self.write_command('?GRATINGS')
        self.grating_densities = []
        self.grating_blazes = []
        for i,number in enumerate(numbers):
            if i%3==0:
                if int(numbers[i])==0:
                    break
                else:
                    self.grating_densities.append(int(numbers[i + 1]))
                    self.grating_blazes.append(int(numbers[i + 2]))
        self.grating_densities=np.array(self.grating_densities)
        self.grating_blazes=np.array(self.grating_blazes)
        self.get_monochromator_parameters()
        logger.info('SP2300 grating info: %s', numbers)
        logger.info('SP2300 grating densities: %s',self.grating_densities)
        logger.info('SP2300 grating blazes: %s',self.grating_blazes)
        logger.info('SP2300 selected grating: %s',self.grating)
        logger.info('SP2300 selected mirror: %s',self.mirror)

        # This is the hardware parameters dictionnary. It is provided by hardware-specific configurations and are not changed in operation
        self.hardware_params=hardware_params
        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        
        self.parameter_display_dict = defaultdict(dict)
        
        self.parameter_dict['central_wave'] = self.center_wl
        self.parameter_dict['grating'] = self.grating
        self.parameter_dict['mirror'] = self.mirror
        
        self.parameter_display_dict['central_wave']['val'] = self.center_wl
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['min'] = 200.00
        self.parameter_display_dict['central_wave']['max'] = 1100.00
        self.parameter_display_dict['central_wave']['read'] = False
        
        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['mirror']['min'] = 1
        self.parameter_display_dict['grating']['max'] = 3
        self.parameter_display_dict['grating']['read'] = False

        self.parameter_display_dict['mirror']['val'] = self.mirror
        self.parameter_display_dict['mirror']['unit'] = ' mirror'
        self.parameter_display_dict['mirror']['min'] = 0
        self.parameter_display_dict['mirror']['max'] = 1
        self.parameter_display_dict['mirror']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']
    
    def write_command(self, cmd):
        """ Command to write to serial handles timeout by blocking serial commands
        Args:
            ser: serial object
            cmd: write command as defined in PI API

        Returns: read string with only digit content. For troubleshooting, consider printing
        the entire answer string
        """
        cmd_bytes = cmd.encode('ASCII')
        self.ser.write(cmd_bytes + b"\r")
        out = bytearray()
        char = b""
        missed_char_count = 0
        while char != b"k":
            char = self.ser.read()
            if char == b"":  # handles a timeout here
                missed_char_count += 1
                self.serial_busy = True
                time.sleep(0.1)
            out += char
        self.serial_busy = False
        return re.findall(r'\d+', out.decode().strip())
   
    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'central_wave':
            cmd = f'{value:0.3f} GOTO'
            self.write_command(cmd)
            self.parameter_dict['center_wave'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'mirror':
            cmd = f'{value:1.0f} MIRROR'
            self.write_command(cmd)
            self.parameter_dict['mirror'] = value
            self.mirror = value

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
                - grating_blazes(np.float): the blaze wavelength of the grating
        """
        self.grating= int(self.write_command('?GRATING')[0])
        self.center_wl = float(self.write_command('?NM')[0])
        self.mirror = int(self.write_command('?MIR')[0])
        return self.center_wl, self.grating_densities[self.grating-1],self.grating_blazes[self.grating-1]

    def get_grating_indices(self):
        """
            Returns the index of the current grating
            output:
                - grating index (int): the index of the grating currently used
                - mirror index(int): the output port the internal mirror is redirecting light to (0 or 1)

        """
        self.grating= int(self.write_command('?GRATING')[0])
        self.center_wl = float(self.write_command('?NM')[0])
        self.mirror = int(self.write_command('?MIR')[0])
        return self.grating,self.mirror