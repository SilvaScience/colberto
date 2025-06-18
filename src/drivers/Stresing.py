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
import logging
import datetime

logger = logging.getLogger(__name__)
class StresingCamera(QtCore.QThread):

    name = 'StresingCamera'

    def __init__(self,hardware_params):
        super(StresingCamera, self).__init__()

        # initialize Worker
        self.worker = StresingWorker()
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.start()
        self.type = 'Camera'

        # This is the hardware parameters dictionnary. It is provided by hardware-specific configurations and are not changed in operation
        self.hardware_params=hardware_params
        self.monochromator=None#By default, no spectrometer is attached
        # Path to the DLL file
        folder_path_dll = Path(__file__).resolve().parent #add or remove parent based on the file location
        path_dll = folder_path_dll / "stresing" / "ESLSCDLL.dll"
        path_dll = str(path_dll)

        path_config = Path(r"C:\Program Files\Stresing\Escam\config.ini")

        # Create a ConfigParser object
        config = configparser.ConfigParser()
        # Read the INI file
        config.read(path_config)

        # Intitalize stresing camera 
        #self.CAM = stresing(path_config, path_dll, path_dll2)
        self.driver = init_driver(self, path_dll, path_config) # type: ignore

        # preallocate arrays
        self.spectrum = np.ndarray([])

        # Parameters. Defines parameters that are required for by the interface
        self.sample = int(config.get("General","nos"))
        self.block = int(config.get("General","nob"))
        self.adc_gain = int(config.get("board0","adcGain"))
        self.channel0 = int(config.get("board0","dacCameraChannel0"))
        self.channel1 = int(config.get("board0","dacCameraChannel1"))
        self.channel2 = int(config.get("board0","dacCameraChannel2"))
        self.channel3 = int(config.get("board0","dacCameraChannel3"))
        self.channel4 = int(config.get("board0","dacCameraChannel4"))
        self.channel5 = int(config.get("board0","dacCameraChannel5"))
        self.channel6 = int(config.get("board0","dacCameraChannel6"))
        self.channel7 = int(config.get("board0","dacCameraChannel7"))
        self.bti = int(config.get("board0","bti"))
        self.sti = int(config.get("board0","sti"))
        self.btimer = int(config.get("board0","btimer"))
        self.stimer = int(config.get("board0","stimer"))
        self.new_spectrum = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['No_Sample']['val'] = self.sample
        self.parameter_display_dict['No_Sample']['unit'] = ' '
        self.parameter_display_dict['No_Sample']['max'] = 4294967295
        self.parameter_display_dict['No_Sample']['read'] = False

        self.parameter_display_dict['No_Block']['val'] = self.block
        self.parameter_display_dict['No_Block']['unit'] = ' '
        self.parameter_display_dict['No_Block']['max'] = 4294967295
        self.parameter_display_dict['No_Block']['read'] = False

        self.parameter_display_dict['ADC_Gain']['val'] = self.adc_gain
        self.parameter_display_dict['ADC_Gain']['unit'] = ' '
        self.parameter_display_dict['ADC_Gain']['max'] = 12
        self.parameter_display_dict['ADC_Gain']['read'] = False

        self.parameter_display_dict['DAC_0']['val'] = self.channel0
        self.parameter_display_dict['DAC_0']['unit'] = ' '
        self.parameter_display_dict['DAC_0']['max'] = 65535
        self.parameter_display_dict['DAC_0']['read'] = False

        self.parameter_display_dict['DAC_1']['val'] = self.channel1
        self.parameter_display_dict['DAC_1']['unit'] = ' '
        self.parameter_display_dict['DAC_1']['max'] = 65535
        self.parameter_display_dict['DAC_1']['read'] = False

        self.parameter_display_dict['DAC_2']['val'] = self.channel2
        self.parameter_display_dict['DAC_2']['unit'] = ' '
        self.parameter_display_dict['DAC_2']['max'] = 65535
        self.parameter_display_dict['DAC_2']['read'] = False

        self.parameter_display_dict['DAC_3']['val'] = self.channel3
        self.parameter_display_dict['DAC_3']['unit'] = ' '
        self.parameter_display_dict['DAC_3']['max'] = 65535
        self.parameter_display_dict['DAC_3']['read'] = False

        self.parameter_display_dict['DAC_4']['val'] = self.channel4
        self.parameter_display_dict['DAC_4']['unit'] = ' '
        self.parameter_display_dict['DAC_4']['max'] = 65535
        self.parameter_display_dict['DAC_4']['read'] = False

        self.parameter_display_dict['DAC_5']['val'] = self.channel5
        self.parameter_display_dict['DAC_5']['unit'] = ' '
        self.parameter_display_dict['DAC_5']['max'] = 65535
        self.parameter_display_dict['DAC_5']['read'] = False

        self.parameter_display_dict['DAC_6']['val'] = self.channel6
        self.parameter_display_dict['DAC_6']['unit'] = ' '
        self.parameter_display_dict['DAC_6']['max'] = 65535
        self.parameter_display_dict['DAC_6']['read'] = False

        self.parameter_display_dict['DAC_7']['val'] = self.channel7
        self.parameter_display_dict['DAC_7']['unit'] = ' '
        self.parameter_display_dict['DAC_7']['max'] = 65535
        self.parameter_display_dict['DAC_7']['read'] = False

        self.parameter_display_dict['Block_Trig']['val'] = self.bti
        self.parameter_display_dict['Block_Trig']['unit'] = ' '
        self.parameter_display_dict['Block_Trig']['max'] = 8
        self.parameter_display_dict['Block_Trig']['read'] = False

        self.parameter_display_dict['Scan_Trig']['val'] = self.sti
        self.parameter_display_dict['Scan_Trig']['unit'] = ' '
        self.parameter_display_dict['Scan_Trig']['max'] = 5
        self.parameter_display_dict['Scan_Trig']['read'] = False

        self.parameter_display_dict['Block_Timer']['val'] = self.btimer
        self.parameter_display_dict['Block_Timer']['unit'] = ' '
        self.parameter_display_dict['Block_Timer']['max'] = 1000000
        self.parameter_display_dict['Block_Timer']['read'] = False

        self.parameter_display_dict['Scan_Timer']['val'] = self.stimer
        self.parameter_display_dict['Scan_Timer']['unit'] = ' '
        self.parameter_display_dict['Scan_Timer']['max'] = 1000000
        self.parameter_display_dict['Scan_Timer']['read'] = False
        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'No_Sample':
            self.parameter_dict['No_Sample'] = value
            self.driver.settings.nos = int(value)
            self.sample = value
            self.new_spectrum = False
        elif parameter == 'No_Block':
            self.parameter_dict['No_Block'] = value
            self.driver.settings.nob = int(value)
            self.block = value
            self.new_spectrum = False
        elif parameter == 'ADC_Gain':
            self.parameter_dict['ADC_Gain'] = value
            self.driver.settings.camera_settings[self.driver.drvno].adc_gain = int(value)
            self.adc_gain = value
            self.new_spectrum = False
        elif parameter == 'DAC_0':
            self.parameter_dict['DAC_0'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][0] = int(value)
            self.channel0 = value
            self.new_spectrum = False
        elif parameter == 'DAC_1':
            self.parameter_dict['DAC_1'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][1] = int(value)
            self.channel1 = value
            self.new_spectrum = False
        elif parameter == 'DAC_2':
            self.parameter_dict['DAC_2'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][2] = int(value)
            self.channel2 = value
            self.new_spectrum = False
        elif parameter == 'DAC_3':
            self.parameter_dict['DAC_3'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][3] = int(value)
            self.channel3 = value
            self.new_spectrum = False
        elif parameter == 'DAC_4':
            self.parameter_dict['DAC_4'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][4] = int(value)
            self.channel4 = value
            self.new_spectrum = False
        elif parameter == 'DAC_5':
            self.parameter_dict['DAC_5'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][5] = int(value)
            self.channel5 = value
            self.new_spectrum = False
        elif parameter == 'DAC_6':
            self.parameter_dict['DAC_6'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][6] = int(value)
            self.channel6 = value
            self.new_spectrum = False
        elif parameter == 'DAC_7':
            self.parameter_dict['DAC_7'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][7] = int(value)
            self.channel7 = value
            self.new_spectrum = False
        elif parameter == 'Block_Trig':
            self.driver.settings.camera_settings[self.driver.drvno].bti_mode = int(value)
            self.bti = value
            self.new_spectrum = False
        elif parameter == 'Scan_Trig':
            self.driver.settings.camera_settings[self.driver.drvno].sti_mode = int(value)
            self.sti = value
            self.new_spectrum = False
        elif parameter == 'Block_Timer':
            self.driver.settings.camera_settings[self.driver.drvno].btime_in_microsec = int(value)
            self.btimer = value
            self.new_spectrum = False
        elif parameter == 'Scan_Timer':
            self.driver.settings.camera_settings[self.driver.drvno].stime_in_microsec = int(value)
            self.stimer = value
            self.new_spectrum = False
        init_measure(self) # type: ignore

    def update_spectrum(self, spectrum):
        self.spectrum = spectrum
        self.new_spectrum = True

    def calculate_wavelength_array(self):
        """
            Calculate the wavelength array for the pixels of the Stresing camera using the hardware parameters from the camera and the attached monochromator. 
        """
        if self.monochromator is not None:
            self.center_wavelength,self.grating_lines_per_mm=self.monochromator.get_monochromator_parameters()
            pixel_size_mm =self.hardware_params['pixel_size_mm'] 
            focal_length_mm = self.hardware_params['focal_length_mm']
            num_pixels = self.hardware_params['num_pixels']

            if self.hardware_params['calibrated']:

                wl_center = self.center_wavelength
                m_order = 1
                px = np.linspace(1,1024,1024)

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

                self.wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
            else:
                # Calculate linear dispersion (nm/mm)
                dispersion = 1e6 / (focal_length_mm * self.grating_lines_per_mm)

                # Center pixel
                center_pixel = num_pixels // 2

                # Pixel index array
                pixel_indices = np.arange(num_pixels)

                # Wavelength at each pixel
                self.wavelengths = self.center_wavelength + (pixel_indices - center_pixel) * dispersion * pixel_size_mm

                # New calibration for screw set at 0 and center wavelength at 650nm
                # Here you can find the data to retreive the linear fit parameters (nm)
                # Theoretical   Measured
                # 365.02        422.30
                # 404.66        463.70
                # 435.83        495.90
                # 546.07        611.90
                # 1013.98       1111.80
                self.wavelengths = 0.9402*self.wavelengths-30.864
        else:
            self.wavelengths= self.hardware_params['num_pixels']
            logger.warning('%s No grating found attached to Stresing. Returning pixels indices instead of wavelength'%datetime.datetime.now())

    def attach_to_monochromator(self,monochromator):
        """
            Attaches the camera to a monochromator, letting the camera interface know where to get the monochromator parameters from.
            input:
                - monochromator (Monochromator QThread): The interface to the monochromator
        """
        self.monochromator=monochromator
        self.type='Spectrometer'
        self.hardware_params.update(self.monochromator.get_hardware_parameters())

    def get_wavelength(self):
        """
            Returns the wavelengths corresponding to each pixel of the camera
        """
        self.calculate_wavelength_array()
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