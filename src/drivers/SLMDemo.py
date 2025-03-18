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
import math as m

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.Slm_Meadowlark_optics import SLM
from src.drivers.Slm_Meadowlark_optics import ImageGen
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from src.compute.SLMBogus import SLM2 


class SLMDemo(QtWidgets.QMainWindow):
    name = 'SLM'

    def __init__(self):
        super(SLMDemo, self).__init__()

        self.slm_worker= SLMWorker()
        self.slm_worker.start()

        
        self.slm_worker.slmParamsSignal.connect(self.handle_slm_params)
        




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

        # set parameters
        self.amplitude = 5

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # load the GUI
        project_folder = os.getcwd()
        uic.loadUi(project_folder + r'\src\GUI\SLM_GUI.ui', self)

        self.slm_worker.newImageSignal.connect(self.update_image_from_array)
       


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
    - Function that updtaded the parameter into the dictionnary
    '''


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




    def update_image_from_array(self, np_img):
    
        """
        Reçoit un numpy array (H x W x 3) en 8 bits, le convertit en QPixmap,
        puis l’affiche dans le QGraphicsView.
        """
        np_img = np.reshape(np_img, (1200, 1920))
        if np_img is None:
            return

        # 1) dimension of the image
        height, width, = np_img.shape
        channels=3

     # 2) Number of octets by line
        bytes_per_line = width  # For an 8 bits (grey level)

    # 3) Create the Qimage in grey scale
        q_img = QImage(np_img.data, width, height, bytes_per_line, QImage.Format_Grayscale8)

    # 4) Convert QImage -> QPixmap
        pixmap = QPixmap.fromImage(q_img)

    # 5) Display in the graphical interface
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)
        self.graphicsView.setScene(scene)



class SLMWorker(QtCore.QThread):
    errorSignal = QtCore.pyqtSignal(str)
    slmParamsSignal = QtCore.pyqtSignal(int, int, int, int, int)
    newImageSignal = QtCore.pyqtSignal(np.ndarray)





    def __init__(self):
        super(SLMWorker, self).__init__() # Elevates this thread to be independent.

           #parameter 
        self._stop_flag = False
        self.current_image = None
        self.isEightBitImage = True
        self.target_fps = 30
        
        self.rgb = True
        self.is_eight_bit = 1
        self.height = 1 
        self.width = 1
        self.depth = 1

        

    '''
    Run function
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


    def run(self):


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

            # Emit a signal to the SLMDemo that update the dictonnary.
            #This is done only 1 time at the beginning, because this parameter doesn't change 
            self.slmParamsSignal.emit(self.height, self.width, self.depth,
                                      self.rgb, self.is_eight_bit)
            


            while not self._stop_flag:
                start_time = time.time()
                
                for i in [0, 1, 2, 3,4,5,6,7,8]:
                    for j in [0,1,2,3,4,5]:
                        start_time = time.time()                                 
                        self.current_image= self.beam_image()
                #self.newImageSignal.emit(self.current_image)
                
                # Éventuellement, si on n’a pas d’image valide, on peut soit
                # afficher un pattern neutre, soit skipper l’envoi
                
           
                


                        if self.current_image is not None:
                    # Envoyer l'image au SLM
                            self.write_image_slm(self.current_image)
                  
                            self.newImageSignal.emit(self.current_image)
                    
                    



                # Calculer le temps écoulé
                        elapsed = time.time() - start_time
                        frame_duration = 1/self.target_fps
                # Si on veut viser 30Hz, on « dort » le reste du temps
                        if elapsed < frame_duration:
                            time.sleep(frame_duration - elapsed)

        except Exception as e:
            # En cas d'erreur, émettre un signal
            self.errorSignal.emit(str(e))
        finally:
            # Nettoyage : libérer le SDK proprement
            if self.slm is not None:
                self.slm.delete_sdk()




    def create_slm_sdk(self):
        #Connect and create the sdk"
        
        slm = SLM()
        slm.create_sdk()
        return slm
    
    #def stop(self):
    #   self._stop_flag = True

    #get the parameter from the slm
    def get_parameter(self):
        slm=SLM()
        h, w, d, rgbCtype, bitCtype=slm.parameter_slm()
        return h, w, d, rgbCtype, bitCtype
    
    #Write image on the slm
    def write_image_slm(self,image):
        slm=SLM()
        slm.write_image(image,c_uint(1))
        return


    def load_lut(self, lut_path):
        """ Load lut file in the SDK Meadowlark."""
        if self.slm is not None:
            self.slm.load_lut(lut_path)
        else:
            print(" Impossible to load the LUT file.") 


    
    def beam_image(self):
        
        slm=SLM()
        cal = Calibration(slm)
        
        
        pix2wave = P(1e-7 * np.array([50000, 1/6000000]))  # Sets bogus polynomial for pix to wave conversion
        cal.set_pixelToWavelength(pix2wave)
        bm = Beam(cal)

        
        bm.set_compressionCarrierWave(532e-9)
        bm.set_optimalPhase(P([0, 0, 1000, 500]))
        bm.set_currentPhase(P([0, 100, 500]), mode='relative')
        #bm.set_beamVerticalDelimiters([1000, 1100])
       
        amplitude = 0.1
        bm.set_gratingAmplitude(amplitude)
        period = 10
        bm.set_gratingPeriod(period)
        image = bm.makeGrating()
        #print(f"Image générée - shape: {image.shape}, taille: {image.size}")
        return image



















"""
    def generate_slm_image(self,i,j):
        '''
    Generating an exemple image for the SLM based on Esteban code. 
    
    Returns:
        np.ndarray: Image en uint8 (1200x1920) <<<(H x W x 3) en 8 bits>>> Ready to write to the slm
        '''
     
    # === Définition des paramètres ===
        A = 2
        d = 128
        chirp = [j, j, i, 0]  # 3, 2, 1, 0 ordre  
        coeff_wavepix = np.array([0.06313, 485])
        w_c = 505
        w_c_delay = 505
        taille = np.array([1920, 1200])  # Taille SLM (Largeur x Hauteur)
        active = np.array([1, 1920, 1, 1920])  # Zone active (adaptée au SLM)
        micaslope = 0
        c = 299792458  # Vitesse de la lumière

    # === Prétraitement du chirp ===
        end = len(chirp) - 1
        for i in range(len(chirp)):
            chirp[end - i] = chirp[end - i] * (1e-15) ** i / m.factorial(i)
        chirp_delay = np.array([chirp[end - 1], 0])
        chirp[end - 1] = 0
        chirp_mica = np.array([micaslope * 1e-15, 0])

        A = A * np.pi
        w_c = 2 * np.pi * c / (w_c * 1e-9)
        w_c_delay = 2 * np.pi * c / (w_c_delay * 1e-9)

    # === Génération de l'image ===
        Image = []

        for i in range(1, taille[1] + 1):  # Balayage ligne par ligne (hauteur)
            if active[0] <= i <= active[1]:
                w = 2 * np.pi * c / (np.polyval(coeff_wavepix, i) * 1e-9)

                if micaslope != 0 and np.mod(i, 2) == 0:
                    offset = np.polyval(chirp, (w - w_c)) / (2 * np.pi)
                    offset += np.polyval(chirp_mica, (w - w_c_delay)) / (2 * np.pi)
                else:
                    offset = np.polyval(chirp, (w - w_c)) / (2 * np.pi)
                    offset += np.polyval(chirp_delay, (w - w_c_delay)) / (2 * np.pi)

                temp = A * np.remainder(1 / d * np.arange(active[2] - 1, active[3], 1) - offset, 1)
                temp = np.pad(temp, (active[2] - 1, taille[0] - active[3]), mode='constant', constant_values=0)
            else:
                temp = np.zeros(taille[0])

            Image.append(temp)

    # === Convertir en tableau numpy et normaliser ===
        Image = np.transpose(np.array(Image))  # Transposer pour correspondre aux dimensions SLM (H x W)
    
    # Normalisation et conversion en uint8
        Image = 255 * (Image - np.min(Image)) / (np.max(Image) - np.min(Image))
        Image = Image.astype(np.uint8)

        data = np.reshape(Image,(1200*1920,)) 

# changing data type from np.float64 to np.uint8
        data = data.astype(np.float64) / np.max(data) # normalize the data to 0 - 1
        data = 255 * data # Now scale by 255
        img = data.astype(np.uint8)
        
        
        return img       

"""
            


   



