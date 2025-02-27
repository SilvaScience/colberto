"""
Created on Tue Feb  06 15:26:53 2025

@author: Mathieu Desmarais
Hardware class to control SLM. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""


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


class SLMDemo(QtWidgets.QMainWindow):
    name = 'SLM'

    def __init__(self):
        super(SLMDemo, self).__init__()

        self.slm_worker= SLMWorker()
        self.slm_worker.start()





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
       

    '''def load_image_gui(self, image_path):
        if not os.path.exists(image_path):
            print(f"Erreur : L'image {image_path} n'existe pas.")
            return

        pixmap = QPixmap(image_path)
    
        # Créer une scène et ajouter l’image
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item) 

    # Assigner la scène au QGraphicsView
        self.graphicsView.setScene(scene)  
        '''
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

    def handle_slm_params(self, height, width, depth, rgb, is8bit):
        # Mettre à jour le parameter_display_dict
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
        print("debut de la fonction update")
        """
        Reçoit un numpy array (H x W x 3) en 8 bits, le convertit en QPixmap,
        puis l’affiche dans le QGraphicsView.
        """
        np_img = np.reshape(np_img, (1200, 1920))
        if np_img is None:
            return

        # 1) Récupérer les dimensions
        height, width, = np_img.shape
        channels=3

        # 1) Récupérer les dimensions (pour une image 2D)
        height, width = np_img.shape
     # 2) Calculer le nombre d'octets par ligne
        bytes_per_line = width  # pour une image 8 bits (niveaux de gris)

    # 3) Créer un QImage en niveaux de gris
        q_img = QImage(np_img.data, width, height, bytes_per_line, QImage.Format_Grayscale8)

    # 4) Convertir QImage -> QPixmap
        pixmap = QPixmap.fromImage(q_img)

    # 5) Afficher dans le QGraphicsView
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)
        self.graphicsView.setScene(scene)



        '''
        # 2) Créer un QImage à partir du numpy array
        #    - On suppose Format_RGB888. Adaptez si vous avez du mono ou autre format.
        bytes_per_line = channels * width
        q_img = QImage(
            np_img.data, 
            width, 
            height, 
            bytes_per_line, 
            QImage.Format_RGB888
        )

        # 3) Convertir QImage -> QPixmap
        pixmap = QPixmap.fromImage(q_img)

        # 4) Afficher dans la QGraphicsView
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)
        self.graphicsView.setScene(scene) 
        
        
        
        print("l'image avant matplotlib")
    # Affichage avec matplotlib (mode non bloquant)
        plt.imshow(np_img, cmap='gray')  # Utilisez cmap='gray' si l'image est en niveaux de gris
        plt.title("Image générée par le worker")
        plt.draw()
        plt.pause(0.001)  # Petite pause pour que la fenêtre se mette à jour
        print("l'image a été affichée avec matplotlib")
        '''





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

        




    def run(self):


        try:
            # 1) Connect to the SDK
            self.slm = self.create_slm_sdk()
            
            self.load_lut(r"C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\19x12_8bit_linearVoltage.lut")



            # 2) Get the slm parameter 
            (h, w, d, rgbCtype, bitCtype) = self.slm.parameter_slm()
            self.height = h
            self.width = w
            self.depth = d
            self.rgb = rgbCtype.value     # ctypes.c_uint -> int
            self.is_eight_bit = bitCtype.value

            #self.slmParamsSignal.emit(self.height, self.width, self.depth,
            #                          self.rgb, self.is_eight_bit)
            


           


            # 2) Boucle principale
            while not self._stop_flag:
                start_time = time.time()
                

                self.current_image= self.generate_slm_image()
                #self.newImageSignal.emit(self.current_image)
                
                # Éventuellement, si on n’a pas d’image valide, on peut soit
                # afficher un pattern neutre, soit skipper l’envoi
                
           
                sys.stdout.flush()  # Forcer l'affichage immédiat


                if self.current_image is not None:
                    # Envoyer l'image au SLM
                    self.slm.write_image(self.current_image,c_uint(1))
                  
                    self.newImageSignal.emit(self.current_image)
                    
                    



                # Calculer le temps écoulé
                elapsed = time.time() - start_time
                frame_duration = 1.0 / self.target_fps
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
    
    def stop(self):
        self._stop_flag = True






    def imageTestSolid(self):
        """
        Exemple de génération d'un motif "solid". 
        On crée d’abord des tableaux array et wfc aux dimensions nécessaires,
        puis on appelle la fonction generate_solid(...) de ImageGen.

        array = 1920 x 1200 x 3  (ou height x width x 3 suivant l’implémentation)
        wfc   = 20 x 1200 x 3    (exemple: correction wavefront)

        Attention à la cohérence hauteur/largeur et l’ordre (height, width).
        """
        # Dans beaucoup de bibliothèques images, la shape est (height, width, channels)
        # Donc si votre SLM fait 1200 de haut et 1920 de large, on dimensionne comme suit:
        height = self.height
        width = self.width
        channels = 3  # si rgb=1

        # Créons un array plein de zéros (8 bits) 
        # Vous pouvez ajuster le dtype en fonction du “depth”
        array = np.zeros((height, width, channels), dtype=np.uint8)

        # wfc peut être un petit tableau (20, width, 3) ou (20, height, 3),
        # selon l’implémentation souhaitée. À adapter !
        wfc = np.zeros((20, width, channels), dtype=np.uint8)

        # Valeur de gris (0 à 255 si 8 bits)
        pixel_val = 128

        # Appel à la fonction generate_solid de ImageGen
        # (vérifiez l’ordre des arguments selon votre signature réelle).
        # La signature indiquée dans votre commentaire :
        # ImageGen.generate_solid(self, array, wfc, width, height, depth, pixel_val, rgb)
        # suppose un ordre d’arguments. Adaptez si besoin.
        '''solid_image = ImageGen.generate_solid(
            array, 
            wfc, 
            width, 
            height, 
            self.depth, 
            pixel_val, 
            self.rgb
            )
            '''
        test_grating = np.empty([width*height], dtype=np.uint8);
        WFC = np.empty([width*height], dtype=np.uint8);
        Period = 128 
        increasing = 0 #0 or 1
        horizontal = 0 #0 or 1
        grating= ImageGen.generate_grating(test_grating.ctypes.data_as(POINTER(c_ubyte)), WFC.ctypes.data_as(POINTER(c_ubyte)), 
                            width, height, self.depth, Period, increasing, horizontal, self.rgb);


        return grating

    def load_lut(self, lut_path):
        """Charge un fichier LUT dans le SDK Meadowlark."""
        if self.slm is not None:
            self.slm.load_lut(lut_path)
        else:
            print("SLM non initialisé. Impossible de charger le LUT.") 


    def generate_slm_image(self):
        """
    Génère une image en utilisant l'algorithme de Esteban et retourne un numpy array.
    
    Returns:
        np.ndarray: Image en uint8 (1200x1920) prête pour affichage sur le SLM.
        """
     
    # === Définition des paramètres ===
        A = 2
        d = 128
        chirp = [0, 0, 0, 0]  # 3, 2, 1, 0 ordre  
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


            


   



