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

from pathlib import Path

class SLMDemo(QtWidgets.QMainWindow):
    name = 'SLM'

    def __init__(self):
        super(SLMDemo, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['temperature']['val'] = 500
        self.parameter_display_dict['temperature']['unit'] = ' K'
        self.parameter_display_dict['temperature']['max'] = 10000
        self.parameter_display_dict['temperature']['read'] = True

        self.parameter_display_dict['amplitude']['val'] = 1
        self.parameter_display_dict['amplitude']['unit'] = ' V'
        self.parameter_display_dict['amplitude']['max'] = 1000
        self.parameter_display_dict['amplitude']['read'] = False

        self.parameter_display_dict['greyscale_val']['val'] = 0
        self.parameter_display_dict['greyscale_val']['unit'] = ' '
        self.parameter_display_dict['greyscale_val']['max'] = 255
        self.parameter_display_dict['greyscale_val']['read'] = False

        # set parameters
        self.amplitude = 5
        self.temperature = 300
        self.greyscale_val = 0

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # load the GUI
        project_folder = Path(__file__).parents[1].resolve()
        uic.loadUi(Path(project_folder,r'GUI/SLM_GUI.ui'), self)

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'amplitude':
            self.parameter_dict['amplitude'] = value
            self.amplitude = value

    def update_image_from_array(self, np_img):

        """
         Receive an numpy array (H x W x 3) in 8 bits, make the conversion in QPixmap,
        and display it in  QGraphicsView.
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

        view_size = self.graphicsView.size()
        scaled_pixmap = pixmap.scaled(view_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

    # 5) Display in the graphical interface
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
        scene.addItem(pixmap_item)
        self.graphicsView.setScene(scene)

    def get_parameters(self):
        #slm = SLM()
        h, w, d, rgbCtype, bitCtype = 1200, 1920, 8, 1, 1
        return h, w, d, rgbCtype, bitCtype

    def write_image_slm(self,image):
        return
