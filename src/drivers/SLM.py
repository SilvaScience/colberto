"""
Created on Tue Feb  06 15:26:53 2025

@author: Mathieu Desmarais
Hardware class to control SLM. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""


from matplotlib import pyplot as plt
from scipy.constants import pi
from numpy.polynomial import Polynomial as P

import numpy as np
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap, QImage
from collections import defaultdict
import matplotlib.pyplot as plt
from ctypes import *
import time
import sys
import os

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.Slm_Meadowlark_optics import SLM
from samples.drivers.exemple_image_generation import beam_image_gen
import logging
import datetime

logger = logging.getLogger(__name__)
class Slm(QtWidgets.QMainWindow):
    name = 'SLM'

    def __init__(self):
        super(Slm, self).__init__()

        self.slm_worker= SLMWorker()
        self.slm_worker.start()
        self.slm_worker.slmParamsSignal.connect(self.handle_slm_params)
        self.slm_worker.slmParamsTemperature.connect(self.handle_slm_temperature)
        
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

    def write_image(self,image):
        """
            Feeds the image into the Worker to be displayed as soon as the SLM is ready
                image: (2d.array of float) The phase image (float from 0 to 2pi)
        """
        self.slm_worker.change_image(image)
        return


class SLMWorker(QtCore.QThread):
    errorSignal = QtCore.pyqtSignal(str)
    slmParamsSignal = QtCore.pyqtSignal(int, int, int, int, int)
    slmParamsTemperature = QtCore.pyqtSignal(int)
    newImageSignal = QtCore.pyqtSignal(np.ndarray)

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
        self.current_image= beam_image_gen()
        logger.info('Made it this far in the interface setup')
        self.new_image_available= True 
        self.frame_duration = 1/self.target_fps
        try:
            # 1) Connect to the SDK
            self.slm = self.create_slm_sdk()
            self.load_lut(r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\19x12_8bit_linearVoltage.lut")

            # 2) Get the slm parameter 
            h, w, d, rgbCtype, bitCtype = self.get_parameter()
            self.height = h
            self.width = w
            self.depth = d
            self.rgb = rgbCtype.value     # ctypes.c_uint -> int
            self.is_eight_bit = bitCtype.value

            # Emit a signal to the interface that update the dictonnary.
            #This is done only 1 time at the beginning, because this parameter doesn't change 
            self.slmParamsSignal.emit(self.height, self.width, self.depth,
                                      self.rgb, self.is_eight_bit)
        except Exception as e:
            # En cas d'erreur, émettre un signal
            logger.error('%s SLM initialization failed at worker startup. Error type %s'%(datetime.datetime.now(),str(e)))
            self.errorSignal.emit(str(e))
            
     

    def run(self):
        '''
        - Begin by initializing the sdk to connect to the SLM with the function -->  create_slm_sdk()
        - Load the callibration file with --> load_lut("path")
        - Get the SLM parameter using the function get_parameter() and emit a signal to SLMDemo()
        - Principal loop
            - Initialize a chronometer to be use to the frameRate specification with time.time()
            - Some loop to send more image. Will need to be remove when the image will be create outside of this code. 
            - Create the image with different chirp (i,j index)
            - Send the image to the SLM with the function  write_image_slm(current_image) and emit a signal to the SLMDemo()
                -- Maybe we could send the image before when the code for the image generation will be done.
            - FrameRate condition. If the time between the initialisation of the image and the writing is less than 30hz sleep for the remaining time 
            - Will need a start stop, at some point if we want to keep the same image 

            
        '''
        self.start_time = time.time()
        while not self.terminate: 
            if self.new_image_available:
                # Calculer le temps écoulé
                elapsed = time.time() - self.start_time
                # Si on veut viser 30Hz, on attends le reste du temps
                if elapsed < self.frame_duration:
                        time.sleep(self.frame_duration - elapsed)
                self.write_image_slm(self.current_image)
                self.start_time = time.time()
                self.newImageSignal.emit(self.current_image)
                self.new_image_available=False
            else:
                self.temperature= self.get_temperature()
                self.slmParamsTemperature.emit(self.temperature)

                
    def change_image(self,image):
        """
            Stores an image in the Worker and signals that a new image is ready to be displayed as soon as the SLM is ready.
            input:
                image: (2d.array of float) The phase image (float from 0 to 2pi)
        """
        self.current_image=image
        self.new_image_available=True

    def create_slm_sdk(self):
        #Connect and create the sdk"
        slm = SLM()
        slm.create_sdk()
        return slm
    
    def get_parameter(self):
        slm=SLM()
        h, w, d, rgbCtype, bitCtype=slm.parameter_slm()
        return h, w, d, rgbCtype, bitCtype
    
    def get_temperature(self):
        slm=SLM()
        temperature=slm.get_slm_temp()
        return temperature
    
    def write_image_slm(self,phase_image):
        '''
            Takes as an input a phase image (float from 0 to 2pi) and displays it on the SLM
            input:
                image: (2d.array of float) The phase image (float from 0 to 2pi)
        '''
        digital_image=self.normalize_phase_image(phase_image)
        self.slm.write_image(digital_image,c_uint(1))
    
    def load_lut(self, lut_path):
        """ Load lut file in the SDK Meadowlark."""
        if self.slm is not None:
            self.slm.load_lut(lut_path)
        else:
            print(" Lut file not found.") 
        
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


















            


   



