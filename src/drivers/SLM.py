"""
Created on Tue Feb  06 15:26:53 2025

@authors: Mathieu Desmarais, Felix Thouin
Hardware class to control SLM. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""


from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial as P

import numpy as np
from PyQt5 import QtWidgets, QtCore, uic
from collections import defaultdict
import matplotlib.pyplot as plt
from ctypes import *
import time
import sys
import os
import configparser
import importlib
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
import logging
import datetime
import tkinter as tk
from tkinter import filedialog

logger = logging.getLogger(__name__)

class Slm(QtCore.QThread):
    """ Interface to the SLM worker thread."""
    name = 'SLM_Meadowlark'
    type= 'SLM'

    def __init__(self):
        super(Slm, self).__init__()
        self.slm_worker= SLMWorker()
        self.slm_worker.slmParamsSignal.connect(self.handle_slm_params)
        self.slm_worker.slmParamsTemperature.connect(self.handle_slm_temperature)
        self.slm_worker.sendFlag.connect(self.set_phaseShown)
        logger.info('%s SLM worker initialized'%datetime.datetime.now())
        self.slm_worker.start()
        logger.info('%s SLM worker running'%datetime.datetime.now())
        self.phaseShown = False
        
        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['Temperature']['val'] = 300
        self.parameter_display_dict['Temperature']['unit'] = ' K'
        self.parameter_display_dict['Temperature']['max'] = 10000
        self.parameter_display_dict['Temperature']['read'] = True

        self.parameter_display_dict['Height']['val'] = 0
        self.parameter_display_dict['Height']['unit'] = ' px'
        self.parameter_display_dict['Height']['max'] = 999999
        self.parameter_display_dict['Height']['read'] = True  # read-only

        self.parameter_display_dict['Width']['val'] = 0
        self.parameter_display_dict['Width']['unit'] = ' px'
        self.parameter_display_dict['Width']['max'] = 999999
        self.parameter_display_dict['Width']['read'] = True

        self.parameter_display_dict['Depth']['val'] = 0
        self.parameter_display_dict['Depth']['unit'] = ' bits'  # ou ce qui fait sens
        self.parameter_display_dict['Depth']['max'] = 99
        self.parameter_display_dict['Depth']['read'] = True

        self.parameter_display_dict['rgb']['val'] = 1
        self.parameter_display_dict['rgb']['unit'] = ' bool'
        self.parameter_display_dict['rgb']['max'] = 1
        self.parameter_display_dict['rgb']['read'] = True

        self.parameter_display_dict['is8bit']['val'] = 1
        self.parameter_display_dict['is8bit']['unit'] = ' bool'  # ou ce qui fait sens
        self.parameter_display_dict['is8bit']['max'] = 1
        self.parameter_display_dict['is8bit']['read'] = True

        self.parameter_display_dict['greyscale_val']['val'] = 0
        self.parameter_display_dict['greyscale_val']['unit'] = ' '
        self.parameter_display_dict['greyscale_val']['max'] = 10000
        self.parameter_display_dict['greyscale_val']['read'] = False

        # set parameters
        self.amplitude = 5
        self.temperature = 300
        self.greyscale_val = 0

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'amplitude':
            self.parameter_dict['amplitude'] = value
            self.amplitude = value
    def get_parameters(self):
        """
            Wrapper that returns the SLM parameters
            returns:
                - SLM height (int8)
                - SLM width (int8)
                - SLM depth(int8)
                - RGB (int8)
                - is8Bit(Bool)

        """
        return self.parameter_dict['Height'],self.parameter_dict['Width'],self.parameter_dict['Depth'],self.parameter_dict['rgb'],self.parameter_dict['is8bit']

    def get_height(self):
        """Wrapper to get SLM height"""
        return self.parameter_dict['Height']

    def get_width(self):
        """Wrapper to get SLM width"""
        return self.parameter_dict['Width']
    
    def get_depth(self):
        """Wrapper to get the SLM depth"""
        return self.parameter_dict['Depth']

    def closeEvent(self, event):
        # Si la fenêtre se ferme, on arrête le worker proprement
        if self.slm_worker.isRunning():
            self.slm_worker.stop()
            self.slm_worker.quit()
            self.slm_worker.wait()
        super().closeEvent(event)

    '''
    - Function that updated the parameter into the dictionary
    '''

    def handle_slm_temperature(self, temperature):
        self.parameter_display_dict['Temperature']['val'] = temperature
        self.parameter_dict['Temperature'] = temperature
    
    def handle_slm_params(self, height, width, depth, rgb, is8bit):
       
        self.parameter_display_dict['Height']['val'] = height
        self.parameter_dict['Height'] = height

        self.parameter_display_dict['Width']['val'] = width
        self.parameter_dict['Width'] = width

        self.parameter_display_dict['Depth']['val'] = depth
        self.parameter_dict['Depth'] = depth

        self.parameter_display_dict['rgb']['val'] = rgb
        self.parameter_dict['rgb'] = rgb

        self.parameter_display_dict['is8bit']['val'] = is8bit
        self.parameter_dict['is8bit'] = is8bit

    def write_image(self,image,imagetype='phase'):
        """
            Feeds the image into the Worker to be displayed as soon as the SLM is ready
                image: (2d.array of float) The image 
                imagetype (str 'phase' (default) or 'raw') Data type in the image. Phase are float from 0 to 2*pi and raw are uint8 from 0 to 255
        """
        logger.info('Just received an image of %d by %d'%image.shape)
        self.phaseShown = False
        self.slm_worker.change_image(image,imagetype=imagetype)

    def set_calibration_wavelength(self, wavelength_m):
        """
            Sets the reference wavelength (in meters) the currently loaded phase-to-greyscale LUT
            was calibrated at. Combined with set_wavelength_axis, this lets each column of an
            image be corrected for the panel's diffraction efficiency dropping away from that
            wavelength before being written to hardware. None disables the correction.
        """
        self.slm_worker.set_calibration_wavelength(wavelength_m)

    def set_wavelength_axis(self, wavelength_axis_m):
        """
            Sets the wavelength (in meters) incident on each SLM column, from the spectral
            calibration.
            input:
                - wavelength_axis_m (np.ndarray): one value per SLM column, same width as the panel
        """
        self.slm_worker.set_wavelength_axis(wavelength_axis_m)

    def load_LUT(self, LUT_path=None):
        if LUT_path is None:
            LUT_path = filedialog.askopenfilename(
                title="Select a file",
                filetypes=[("Text files", "*.lut"), ("All files", "*.*")]
            )
        print('Importing the LUT file...')
        self.slm_worker.load_lut(LUT_path)
        return LUT_path

    def set_phaseShown(self, phaseShown):
        self.phaseShown = phaseShown
    
    def check_phaseShown(self):
        if self.phaseShown == True:
            return True
        else:
            return False

class SLMWorker(QtCore.QThread):
    """Worker thread that host the SLM instantiation."""
    errorSignal = QtCore.pyqtSignal(str)
    slmParamsSignal = QtCore.pyqtSignal(int, int, int, int, int)
    slmParamsTemperature = QtCore.pyqtSignal(int)
    imageSLM = QtCore.pyqtSignal(np.ndarray)
    sendFlag = QtCore.pyqtSignal(bool)
    
    def __init__(self):
        super(SLMWorker, self).__init__() # Elevates this thread to be independent.

        path_config = Path(r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\config_UdeM.ini")

        # Create a ConfigParser object
        config = CaseInsensitiveConfig()
        # Read the INI file
        config.read(path_config)
    
        #parameter 
        self.terminate= False
        self.target_fps = 30
        self.slm = None
        self.driver_name = config.get("SLM0","driverName")
        self.c_wrapper = config.get("SLM0","cWrapper")
        self.image_Gen = config.get("SLM0","imageGen")
        self.lut_File = config.get("SLM0","lutFile")
        self.rgb = int(config.get("SLM0","rgb"))
        self.is_eight_bit_image = int(config.get("SLM0","isEightBitImage"))
        self.height = int(config.get("SLM0","height")) 
        self.width = int(config.get("SLM0","width"))
        self.depth = int(config.get("SLM0","depth"))
        self.bytes_per_pixel = int(config.get("SLM0","bytesPerPixel"))
        self.current_image = np.zeros((self.width,self.height,3))
        self.new_image_available = False
        self.frame_duration = 1/self.target_fps

        # Wavelength-dependent correction of the phase-to-greyscale LUT (see set_calibration_wavelength/
        # set_wavelength_axis). Both must be set before any correction is applied; until then this is a
        # no-op, matching the previous single-wavelength behaviour.
        self.calibration_wavelength = None
        self.wavelength_axis = None
        self._last_clip_warning_time = 0.0
        self.phaseShown = False

    def run(self):
        '''
        - Begin by initializing the sdk to connect to the SLM with the function -->  create_slm_sdk()
        - Load the callibration file with --> load_lut("path")
        - Get the SLM parameter using the function get_parameter() and emit a signal to SLMDemo()
        - Principal loop
            - Initialize a chronometer to be use to the frameRate specification with time.time()
                - FrameRate condition. If the time between the initialisation of the image and the writing is less than 30hz sleep for the remaining time 
            - Checks if the image has been changed and if it is ready to be updated, otherwise measures the temperature.
            
        '''
        try:
            # 1) Connect to the SDK
            print('Connecting the SLM...')
            self.slm = self.create_slm_sdk()
            print('Importing the LUT file...')
            # IMPORTANT: These lines only need to be run once to store the LUT to nonvolatile memory. If you want to change the LUT file, it's preferable to use the BlinkHDMI software directly. 
            self.load_lut(self.lut_File)
            logger.info('%s SLM Worker initialization success.'%datetime.datetime.now())
            print('SLM conneted')
        except Exception as e:
            # En cas d'erreur, émettre un signal
            logger.error('%s SLM initialization failed at worker startup. Error type %s'%(datetime.datetime.now(),str(e)))
            self.errorSignal.emit(str(e))
            raise
        # 2) Get the slm parameter 
        self.get_parameter()
        self.get_temperature()
        self.start_time = time.time()
        while not self.terminate:
            ## Calculer le temps écoulé
            elapsed = time.time() - self.start_time
            ## Si on veut viser 30Hz, on attends le reste du temps
            time.sleep(1e-3)
            if elapsed >= self.frame_duration:
                if self.new_image_available:
                    try:
                        self.write_image_slm()
                        self.start_time = time.time()
                        self.new_image_available=False
                    except Exception as e:
                        logger.error('Error when displaying image at the SLM %s'%e)
                        raise
                else:
                    self.get_temperature()
                    self.start_time = time.time()
                
    def change_image(self,image,imagetype='phase'):
        """
            Stores an image in the Worker and signals that a new image is ready to be displayed as soon as the SLM is ready.
            input:
                image: (2d.array of float) The image 
                imagetype (str 'phase' (default) or 'raw') Data type in the image. Phase are float from 0 to 2*pi and raw are uint8 from 0 to 255
        """

        if imagetype=='phase':
            digital_image=self.slm.normalize_phase_image(image)
            digital_image=self.apply_wavelength_correction(digital_image, max_value=2**self.depth-1)
        if imagetype=='raw':
            digital_image=image
        self.current_image=digital_image
        self.new_image_available=True
        self.phaseShown = False

    def set_calibration_wavelength(self, wavelength_m):
        """
            Sets the reference wavelength (in meters) the currently loaded phase-to-greyscale LUT
            was calibrated at. None (default) disables the wavelength correction.
        """
        self.calibration_wavelength = wavelength_m

    def set_wavelength_axis(self, wavelength_axis_m):
        """
            Sets the wavelength (in meters) incident on each SLM column, from the spectral
            calibration.
            input:
                - wavelength_axis_m (np.ndarray): one value per SLM column, same width as the panel
        """
        self.wavelength_axis = wavelength_axis_m

    def apply_wavelength_correction(self, digital_image, max_value):
        """
            Scales each column of a greyscale image by wavelength(column)/calibration_wavelength.

            The phase-to-greyscale LUT is calibrated at a single reference wavelength: sending the
            greyscale value computed for that reference to a column actually carrying a different
            wavelength produces the wrong retardance there, and therefore the wrong diffraction
            efficiency (see beam_management.md / LUT calibration discussion). Returns the image
            unchanged if no calibration wavelength or wavelength axis has been set yet.
            input:
                - digital_image (np.ndarray): greyscale image, shape (height, width)
                - max_value (int): saturation value of the greyscale range (255 or 1023)
            output:
                - np.ndarray: corrected image, same shape and dtype as digital_image
        """
        if self.calibration_wavelength is None or self.wavelength_axis is None:
            return digital_image
        if self.wavelength_axis.shape[0] != digital_image.shape[1]:
            logger.warning('%s SLM wavelength axis length (%d) does not match image width (%d); '
                           'skipping wavelength correction.'
                           % (datetime.datetime.now(), self.wavelength_axis.shape[0], digital_image.shape[1]))
            return digital_image

        dtype = digital_image.dtype
        ratio = self.wavelength_axis / self.calibration_wavelength
        corrected = digital_image.astype(np.float64) * ratio[np.newaxis, :]
        clipped = np.clip(corrected, 0, max_value)

        if not np.array_equal(clipped, corrected):
            now = time.time()
            if now - self._last_clip_warning_time > 1.0:
                n_clipped = int(np.count_nonzero(clipped != corrected))
                logger.warning('%s SLM wavelength correction clipped %d pixel(s): requested phase '
                               'exceeds what the panel can produce at the local wavelength.'
                               % (datetime.datetime.now(), n_clipped))
                self._last_clip_warning_time = now

        return np.round(clipped).astype(dtype)

    def create_slm_sdk(self):
        """
            Instantiate the SLM driver and create the SDK
        """
        module = importlib.import_module(f"src.drivers.{self.driver_name}")
        self.slm = module.SLM(self.c_wrapper, self.image_Gen)
        self.slm.sendFlag.connect(self.set_phaseShown)
        self.slm.create_sdk()
        return self.slm
    
    def get_parameter(self):
        """
            Retrieves the hardware parameters of the SLM
        """
        h, w, d, rgbCtype, bitCtype=self.slm.parameter_slm()
        self.height = h
        self.width = w
        self.depth = d
        self.rgb = rgbCtype.value     # ctypes.c_uint -> int
        self.is_eight_bit_image = bitCtype.value

        # Emit a signal to the interface that update the dictonnary.
        #This is done only 1 time at the beginning, because this parameter doesn't change 
        self.slmParamsSignal.emit(self.height, self.width, self.depth,
                                    self.rgb, self.is_eight_bit_image)
        return h, w, d, rgbCtype, bitCtype
    
    def get_temperature(self):
        """
            Queries the temperature from the SLM driver and emits the signal
        """
        #self.temperature=self.slm.get_slm_temp()
        #self.slmParamsTemperature.emit(int(self.temperature))
    
    def write_image_slm(self):
        '''
            Takes as an input a phase image (float from 0 to 2pi) and displays it on the SLM
            input:
                image: (nd.array of uint8) The digital image (0 to 255 uint 8 3 channel RGB)
        '''
        self.imageSLM.emit(self.current_image)
        self.slm.write_image(self.current_image)
    
    def load_lut(self, lut_path):
        """ Load lut file in the SDK Meadowlark."""
        if self.slm is not None:
            self.slm.load_lut(lut_path)
            print(lut_path)
        else:
            logger.error('%s  Lut file not found.'%datetime.datetime.now())

    def set_phaseShown(self, phaseShown):
        self.phaseShown = phaseShown
        self.sendFlag.emit(phaseShown)
    
    def close(self):
        """
            Shutdown routine for the SLM Worker and SLM
        """
        if self.slm is not None:
            self.slm.delete_sdk()

class CaseInsensitiveConfig(configparser.ConfigParser):
    """ This class extends Python’s built-in configparser.ConfigParser to make both section names and option names case-insensitive.
    Normally, ConfigParser is only case-insensitive for option names, not section names, so this subclass enforces lowercase normalization for both. """

    def __init__(self, *args, **kwargs):
        """
            Initialize the parent ConfigParser. By inheriting from it, your class gets all the functionality of ConfigParser — things like: 
                Reading .ini files
                Parsing sections and options
                Providing .get(), .set(), .items(), etc.
            Then you can override or extend parts of that functionality to make it case-insensitive.
        """
        super().__init__(*args, **kwargs)

        # Force all option (key) names to be lowercase when stored internally
        # This makes option lookups case-insensitive
        self.optionxform = str.lower

    def read(self, filenames, encoding=None):
        """
            Use the parent class's read method to load the config file(s)
        """
        super().read(filenames, encoding)

        # Convert all section names and their corresponding option names to lowercase
        # This ensures that both sections and options are case-insensitive
        self._sections = {
            k.lower(): {kk.lower(): vv for kk, vv in v.items()}
            for k, v in self._sections.items()
        }

    def get(self, section, option, **kwargs):
        """
            Override the default .get() method so that lookups are case-insensitive
        """
        # Both section and option names are converted to lowercase before lookup
        return super().get(section.lower(), option.lower(), **kwargs)