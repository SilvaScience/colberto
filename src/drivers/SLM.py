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

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.Slm_Meadowlark_optics import SLM
import logging
import datetime
from numpy.polynomial import Polynomial


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
        logger.info('%s SLM worker initialized'%datetime.datetime.now())
        self.slm_worker.start()
        logger.info('%s SLM worker running'%datetime.datetime.now())
        self.calibration_file = None
        self.phase2gray_coeffs = None
        self.pixelToWavelength = None

        
        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['temperature']['val'] = 300
        self.parameter_display_dict['temperature']['unit'] = ' K'
        self.parameter_display_dict['temperature']['max'] = 10000
        self.parameter_display_dict['temperature']['read'] = True

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
        self.parameter_display_dict['greyscale_val']['max'] = 255
        self.parameter_display_dict['greyscale_val']['read'] = False

        # set parameters
        self.amplitude = 5
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
        self.parameter_display_dict['temperature']['val'] = temperature
        self.parameter_dict['temperature'] = temperature
    
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
        #logger.info('Just received an image of %d by %d'%image.shape)
        logger.info("Just received an image of %d by %d at %s", image.shape[0], image.shape[1], datetime.datetime.now())
        self.slm_worker.change_image(image,imagetype=imagetype)

    def process_Phase2Gray_calibration(self, filepath):
        """
        Loads and stores SLM calibration coefficients from a CSV or TXT file.
        """
        try:
            self.calibration_file = filepath
            self.phase2gray_coeffs = np.loadtxt(filepath, delimiter=',', skiprows=1)
            #print(f"Loaded SLM calibration from: {filepath}")
            logger.info(f"Loaded SLM calibration from: {filepath}")
            #print(f"Shape of coeffs: {self.phase2gray_coeffs.shape}")
            logger.info(f"Shape of coeffs: {self.phase2gray_coeffs.shape}")

            self.slm_worker.phase2gray_coeffs = self.phase2gray_coeffs
            logger.info('calibration coeffs sent to SLMWorker')

            print(f"Type of my_list: {type(self.phase2gray_coeffs)}")

        except Exception as e:
            print(f"Error loading SLM calibration: {e}")
            self.phase2gray_coeffs = None
            raise

    def set_pixelToWavelength(self,polynomial):
        '''
        Sets the pixel to wavelength calibration polynomial for this beam
        input:
            - polynomial: (Polynomial object) a Numpy Power series polynomial relating a pixel index to a wavelength in m
        '''
        self.pixelToWavelength=polynomial
        print(self.pixelToWavelength)

    def normalize_phase_image(self,image, max_phase=2 * np.pi):
        """
        Convert a float64 phase image (0 to 2π) to uint8 (0 to 255).
        """
        image = np.clip(image, 0, max_phase)  # safety
        norm_img = (image / max_phase) * 255
        return norm_img.astype(np.uint8)

    def phase2gray(self, phase_image):
        """
        Convert a phase image to grayscale values using the wavelength-dependent calibration.
        Each SLM column is assigned a wavelength using the stored pixel→wavelength polynomial.

        Parameters
        ----------
        phase_image : np.ndarray
            2D phase image (radians).
        self.phase2gray_coeffs : np.ndarray, optional
            Table of polynomial coefficients mapping phase→gray per wavelength, shape (Nwaves, 6)
            [wavelength, a5, a4, a3, a2, a1, a0].

        Returns
        -------
        gray_image : np.ndarray
            2D array (same shape as phase_image) with grayscale values [0–255].
        """

        # --- 1. Get or create wavelength mapping across SLM columns ---
        if self.pixelToWavelength is None:
            # fallback: use provided coefficients (if calibration not loaded)
            poly_coeffs = [691.50709535, 95.41146932, -0.03298118, 0.38760572, 0.00850083, -0.33233454]
            pixel_to_wavelength = Polynomial(poly_coeffs)
            print("Created synthetic pixel→wavelength calibration")

        else:
            pixel_to_wavelength = self.pixelToWavelength
            print("Using loaded pixel→wavelength calibration")

        # --- 3. Loop through each column and apply wavelength-dependent phase→gray mapping ---
        if self.phase2gray_coeffs is None:
            raise ValueError("phase2gray_coeffs (the LUT) must be provided.")

        cal_wavelengths = self.phase2gray_coeffs[:, 0]
        coeff_table = self.phase2gray_coeffs[:, 1:]  # shape: (N, 5 or 6)

        width = self.get_width()
        height = self.get_height()
        wavelengths_per_column = pixel_to_wavelength(width)

        # Interpolate coefficients for each column based on wavelength
        coeffs_interp = np.empty((width, coeff_table.shape[1]))
        for i in range(coeff_table.shape[1]):
            coeffs_interp[:, i] = np.interp(wavelengths_per_column, cal_wavelengths, coeff_table[:, i])

        # Create an empty grayscale image matching the input
        gray_image = np.zeros((height, width), dtype=np.float32)

        # --- 4. Compute grayscale for each pixel column ---
        for col in range(width):
            coeffs = coeffs_interp[col]
            # polynomial order should match your LUT (assumed 5th-order)
            gray_image[:, col] = (
                    coeffs[0] * phase_image[:, col] ** 5 +
                    coeffs[1] * phase_image[:, col] ** 4 +
                    coeffs[2] * phase_image[:, col] ** 3 +
                    coeffs[3] * phase_image[:, col] ** 2 +
                    coeffs[4] * phase_image[:, col] +
                    coeffs[5]
            )

        # --- 5. Normalize and clip ---
        #gray_image = np.clip(gray_image, 0, 255).astype(np.uint8)

        print("phase2gray: completed normalization using pixel→wavelength calibration.")

        return gray_image


class SLMWorker(QtCore.QThread):
    """Worker thread that host the SLM instantiation."""
    errorSignal = QtCore.pyqtSignal(str)
    slmParamsSignal = QtCore.pyqtSignal(int, int, int, int, int)
    slmParamsTemperature = QtCore.pyqtSignal(int)
    imageSLM=QtCore.pyqtSignal(np.ndarray)

    def __init__(self):
        super(SLMWorker, self).__init__() # Elevates this thread to be independent.

        #parameter 
        self.terminate= False
        self.isEightBitImage = True
        self.target_fps = 30
        self.slm=None 
        self.rgb = True
        self.is_eight_bit = 1
        self.height = 1 
        self.width = 1
        self.depth = 1
        self.current_image= np.zeros((self.width,self.height,3))
        self.new_image_available= False 
        self.frame_duration = 1/self.target_fps
        self.phase2gray_coeffs = None

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
            self.slm = self.create_slm_sdk()
            self.load_lut(r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\19x12_8bit_linearVoltage.lut")
            logger.info('%s SLM Worker initialization success.'%datetime.datetime.now())
        except Exception as e:
            # En cas d'erreur, émettre un signal
            logger.error('%s SLM initialization failed at worker startup. Error type %s'%(datetime.datetime.now(),str(e)))
            self.errorSignal.emit(str(e))
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
            digital_image=self.normalize_phase_image(image)
        if imagetype=='raw':
            digital_image=image
        self.current_image=digital_image
        self.new_image_available=True

    def create_slm_sdk(self):
        """
            Instantiate the SLM driver and create the SDK
        """
        slm = SLM()
        slm.create_sdk()
        return slm
    
    def get_parameter(self):
        """
            Retrieves the hardware parameters of the SLM
        """
        h, w, d, rgbCtype, bitCtype=self.slm.parameter_slm()
        self.height = h
        self.width = w
        self.depth = d
        self.rgb = rgbCtype.value     # ctypes.c_uint -> int
        self.is_eight_bit = bitCtype.value

        # Emit a signal to the interface that update the dictonnary.
        #This is done only 1 time at the beginning, because this parameter doesn't change 
        self.slmParamsSignal.emit(self.height, self.width, self.depth,
                                    self.rgb, self.is_eight_bit)
        return h, w, d, rgbCtype, bitCtype
    
    def get_temperature(self):
        """
            Queries the temperature from the SLM driver and emits the signal
        """
        self.temperature=self.slm.get_slm_temp()
        self.slmParamsTemperature.emit(self.temperature)
    
    def write_image_slm(self):
        '''
            Takes as an input a phase image (float from 0 to 2pi) and displays it on the SLM
            input:
                image: (nd.array of uint8) The digital image (0 to 255 uint 8 3 channel RGB)
        '''
        self.imageSLM.emit(self.current_image)
        #logger.info('Worker received SLM image to change')
        self.slm.write_image(self.current_image.reshape(-1),c_uint(1))
    
    def load_lut(self, lut_path):
        """ Load lut file in the SDK Meadowlark."""
        if self.slm is not None:
            self.slm.load_lut(lut_path)
        else:
            logger.error('%s  Lut file not found.'%datetime.datetime.now())
        
    def normalize_phase_image(self,image, max_phase=2 * np.pi):
        """
        Convert a float64 phase image (0 to 2π) to uint8 (0 to 255).
        """
        image = np.clip(image, 0, max_phase)  # safety
        norm_img = (image / max_phase) * 255
        return norm_img.astype(np.uint8)

    def close(self):
        """
            Shutdown routine for the SLM Worker and SLM
        """
        if self.slm is not None:
            self.slm.delete_sdk()






















            


   



