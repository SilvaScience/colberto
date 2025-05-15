"""
Created on Fri Feb 07 15:26:53 2025

@author: Simon Daneau
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""
"""TO DOS:
- think of TO DOs
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
from pathlib import Path
import matplotlib.pyplot as plt
from drivers.StresingDriver import camera_settings
from drivers.StresingDriver import measurement_settings
from drivers.StresingDriver import *
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import configparser

class StresingCamera(QtCore.QThread):

    name = 'StresingCamera'
    type = 'Camera'

    def __init__(self,hardware_params):
        super(StresingCamera, self).__init__()

        # initialize Worker
        self.worker = StresingWorker()
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.start()

        self.hardware_params=hardware_params
        self.update_grating()
        self.calculate_wavelength_array()

        # Path to the DLL file
        folder_path = Path(__file__).resolve().parent #add or remove parent based on the file location

        path_dll = folder_path / "Stresing" / "ESLSCDLL.dll"
        path_dll = str(path_dll)

        path_config = folder_path / "Stresing" / "config_UdeM.ini"
        path_config = str(path_config)

        # Create a ConfigParser object
        config = configparser.ConfigParser()
        # Read the INI file
        config.read(path_config)

        # Intitalize stresing camera 
        #self.CAM = stresing(path_config, path_dll, path_dll2)
        self.driver= init_driver(self, path_dll, path_config) # type: ignore

        # preallocate arrays
        self.spectrum = np.ndarray([])

        # Parameters. Defines parameters that are required for by the interface
        self.sample = int(config.get("General","nos"))
        self.block = int(config.get("General","nob"))
        self.adc_gain = int(config.get("Board0","adcGain"))
        self.channel0 = int(config.get("Board0","dacCameraChannel0"))
        self.channel1 = int(config.get("Board0","dacCameraChannel1"))
        self.channel2 = int(config.get("Board0","dacCameraChannel2"))
        self.channel3 = int(config.get("Board0","dacCameraChannel3"))
        self.channel4 = int(config.get("Board0","dacCameraChannel4"))
        self.channel5 = int(config.get("Board0","dacCameraChannel5"))
        self.channel6 = int(config.get("Board0","dacCameraChannel6"))
        self.channel7 = int(config.get("Board0","dacCameraChannel7"))
        self.new_spectrum = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['sample']['val'] = self.sample
        self.parameter_display_dict['sample']['unit'] = ' '
        self.parameter_display_dict['sample']['max'] = 4294967295
        self.parameter_display_dict['sample']['read'] = False

        self.parameter_display_dict['block']['val'] = self.block
        self.parameter_display_dict['block']['unit'] = ' '
        self.parameter_display_dict['block']['max'] = 4294967295
        self.parameter_display_dict['block']['read'] = False

        self.parameter_display_dict['adc_gain']['val'] = self.adc_gain
        self.parameter_display_dict['adc_gain']['unit'] = ' '
        self.parameter_display_dict['adc_gain']['max'] = 12
        self.parameter_display_dict['adc_gain']['read'] = False

        self.parameter_display_dict['DAC0']['val'] = self.channel0
        self.parameter_display_dict['DAC0']['unit'] = ' '
        self.parameter_display_dict['DAC0']['max'] = 65535
        self.parameter_display_dict['DAC0']['read'] = False

        self.parameter_display_dict['DAC1']['val'] = self.channel1
        self.parameter_display_dict['DAC1']['unit'] = ' '
        self.parameter_display_dict['DAC1']['max'] = 65535
        self.parameter_display_dict['DAC1']['read'] = False

        self.parameter_display_dict['DAC2']['val'] = self.channel2
        self.parameter_display_dict['DAC2']['unit'] = ' '
        self.parameter_display_dict['DAC2']['max'] = 65535
        self.parameter_display_dict['DAC2']['read'] = False

        self.parameter_display_dict['DAC3']['val'] = self.channel3
        self.parameter_display_dict['DAC3']['unit'] = ' '
        self.parameter_display_dict['DAC3']['max'] = 65535
        self.parameter_display_dict['DAC3']['read'] = False

        self.parameter_display_dict['DAC4']['val'] = self.channel4
        self.parameter_display_dict['DAC4']['unit'] = ' '
        self.parameter_display_dict['DAC4']['max'] = 65535
        self.parameter_display_dict['DAC4']['read'] = False

        self.parameter_display_dict['DAC5']['val'] = self.channel5
        self.parameter_display_dict['DAC5']['unit'] = ' '
        self.parameter_display_dict['DAC5']['max'] = 65535
        self.parameter_display_dict['DAC5']['read'] = False

        self.parameter_display_dict['DAC6']['val'] = self.channel6
        self.parameter_display_dict['DAC6']['unit'] = ' '
        self.parameter_display_dict['DAC6']['max'] = 65535
        self.parameter_display_dict['DAC6']['read'] = False

        self.parameter_display_dict['DAC7']['val'] = self.channel7
        self.parameter_display_dict['DAC7']['unit'] = ' '
        self.parameter_display_dict['DAC7']['max'] = 65535
        self.parameter_display_dict['DAC7']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'sample':
            self.parameter_dict['sample'] = value
            self.settings.nos = int(value)
            self.sample = value
            self.new_spectrum = False
        elif parameter == 'block':
            self.parameter_dict['block'] = value
            self.settings.nob = int(value)
            self.block = value
            self.new_spectrum = False
        elif parameter == 'adc_gain':
            self.parameter_dict['adc_gain'] = value
            self.settings.camera_settings[self.drvno].adc_gain = int(value)
            self.adc_gain = value
            self.new_spectrum = False
        elif parameter == 'DAC0':
            self.parameter_dict['DAC0'] = value
            self.settings.camera_settings[0].dac_output[0][0] = int(value)
            self.channel0 = value
            self.new_spectrum = False
        elif parameter == 'DAC1':
            self.parameter_dict['DAC1'] = value
            self.settings.camera_settings[0].dac_output[0][1] = int(value)
            self.channel1 = value
            self.new_spectrum = False
        elif parameter == 'DAC2':
            self.parameter_dict['DAC2'] = value
            self.settings.camera_settings[0].dac_output[0][2] = int(value)
            self.channel2 = value
            self.new_spectrum = False
        elif parameter == 'DAC3':
            self.parameter_dict['DAC3'] = value
            self.settings.camera_settings[0].dac_output[0][3] = int(value)
            self.channel3 = value
            self.new_spectrum = False
        elif parameter == 'DAC4':
            self.parameter_dict['DAC4'] = value
            self.settings.camera_settings[0].dac_output[0][4] = int(value)
            self.channel4 = value
            self.new_spectrum = False
        elif parameter == 'DAC5':
            self.parameter_dict['DAC5'] = value
            self.settings.camera_settings[0].dac_output[0][5] = int(value)
            self.channel5 = value
            self.new_spectrum = False
        elif parameter == 'DAC6':
            self.parameter_dict['DAC6'] = value
            self.settings.camera_settings[0].dac_output[0][6] = int(value)
            self.channel6 = value
            self.new_spectrum = False
        elif parameter == 'DAC7':
            self.parameter_dict['DAC7'] = value
            self.settings.camera_settings[0].dac_output[0][7] = int(value)
            self.channel7 = value
            self.new_spectrum = False
        init_measure(self) # type: ignore

    def update_spectrum(self, spectrum):
        self.spectrum = spectrum
        self.new_spectrum = True
    
    def update_grating(self,center_wavelength,grating_lines_per_mm):
        """
            Update the grating parameters and calculates the new wavelength axes of the spectrum returned by the spectrometer.
            input:
                - center_wavelength (np.float): The nominal wavelength (in nm) at the center pixel of the detector array
                - grating_lines_per_mm (np.float): The dispersion (lines per mm) of the grating used
        """
        self.center_wavelength=center_wavelength
        self.grating_lines_per_mm=grating_lines_per_mm
        self.calculate_wavelength_array()

    def calculate_wavelength_array(self):
        """
            Calculate the wavelength array for the pixels of the Stresing camera
        """
        pixel_size_mm =self.hardware_params['pixel_size_mm'] 
        focal_length_mm = self.hardware_params['focal_length_mm']
        num_pixels = self.hardware_params['num_pixels']

        if self.hardware_params['calibrated']:

            wl_center = center_wavelength_nm
            m_order = 1
            px = self.px0

            # calibration from notebook
            f=self.hardware_params['f']
            delta=self.hardware_params['delta']
            gamma=self.hardware_params['gamma']
            n0=self.hardware_params['n0']
            offset_adjust=self.hardware_params['offset_adjust']
            d_grating=self.hardware_params['d_grating']
            x_pixel=self.hardware_params['x_pixel']
            curvature=self.hardware_params['curvature']

            n = px - (n0 + offset_adjust * wl_center)

            # print('psi top', m_order* wl_center)
            # print('psi bottom', (2*d_grating*np.cos(gamma/2)) )

            psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
            eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))

            wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
        else:
            # Calculate linear dispersion (nm/mm)
            dispersion = 1e6 / (focal_length_mm * self.grating_lines_per_mm)

            # Center pixel
            center_pixel = num_pixels // 2

            # Pixel index array
            pixel_indices = np.arange(num_pixels)

            # Wavelength at each pixel
            self.wavelengths = self.center_wavelength_nm + (pixel_indices - center_pixel) * dispersion * pixel_size_mm


    def get_wavelength(self):
        return self.wavelengths

    def get_intensities(self):
        use_blocking_call = True
        self.spectrum = StresingWorker.worker_spectrum(self, use_blocking_call)
        while not self.new_spectrum:
            time.sleep(0.01)
            self.new_spectrum = False
        return self.spectrum

class StresingWorker(QtCore.QThread):
    """ This is a DemoWorker for the Stresing Camera.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an ac_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changing settings.  """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray)

    def __init__(self):
        super(StresingWorker, self).__init__() # Elevates this thread to be independent.
        self.spectrum = np.zeros(self.spec_length)
        self.new_spectrum = False

    def run(self):
        while True:
            time.sleep(0.01)
            if self.new_spectrum:
                self.new_spectrum = False
                self.sendSpectrum.emit(self.spectrum)
            pass

    def worker_spectrum(self, use_blocking_call):
        init_measure(self) # type: ignore
        self.spectrum = measure(self, use_blocking_call) # type: ignore
        self.new_spectrum = True
        return self.spectrum