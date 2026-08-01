
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

class SpectraPro2300i(QtCore.QThread):
    
    name = 'SpectraPro2300i'
    type = 'Monochromator'
    
    def __init__(self,hardware_params):
        super(SpectraPro2300i, self).__init__()

        # set up spectrograph
        self.serial_busy = False
        port = 'COM5'
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        numbers = self.write_command('?GRATINGS')
        """ Uninstalled turret positions answer with their index and nothing else, so the number of
        gratings cannot be derived from the length of the reply: (len - 8) / 2 counted 4 on a turret
        holding 3, and invented a grating of 4 lines/mm. Walk the triples instead and stop at the
        first implausible groove density. The parsing stays fragile because write_command() keeps
        only the digits, which also splits a blaze written as "2.0UM" into 2 and 0. """
        densities, blazes = [], []
        for i in range(0, len(numbers) - 2, 3):
            density = float(numbers[i + 1])
            if density < 50:
                break
            densities.append(density)
            blazes.append(float(numbers[i + 2]))
        self.num_gratings = len(densities)
        self.grating_densities = np.array(densities)
        self.grating_blazes = np.array(blazes)
        self.center_wl = float(self.write_command('?NM')[0])
        self.mirror = float(self.write_command('?MIR')[0])
        print(self.center_wl)
        print(self.grating_densities)
        print(self.grating_blazes)
        print(self.grating)
        print('SP2300 grating info: ', numbers)
        print('SP2300 grating densities: ',self.grating_densities)
        print('SP2300 grating blazes: ',self.grating_blazes)
        print('SP2300 selected grating: ',self.grating)

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
        """ The loop used to wait for the terminating 'k' of "ok" with no way out: missed_char_count
        was counted and never acted on, so a controller that stopped answering froze whoever called
        this, which is the GUI thread. The deadline is generous rather than tight because a turret
        move answers nothing at all until it has finished. """
        deadline = time.time() + 60
        while char != b"k":
            if time.time() > deadline:
                self.serial_busy = False
                raise TimeoutError('No reply to %r after 60 s (got %r)' % (cmd, bytes(out)))
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
            self.parameter_dict['central_wave'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'mirror':
            """ The controller ignores "<n> MIRROR": it answers ok and leaves the mirror where it is,
            so this silently did nothing. The exit mirror is selected with EXIT-MIRROR and then driven
            with FRONT or SIDE. Checked on the SP-2-300i, serial 23581080: after moving to front,
            "1 MIRROR" left ?MIRROR reading front, while EXIT-MIRROR followed by SIDE moved it.
            ?MIR reports 0 for front and 1 for side. """
            self.write_command('EXIT-MIRROR')
            self.write_command('SIDE' if int(value) else 'FRONT')
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
        """
        return self.center_wl, self.grating_densities[int(self.grating-1)]