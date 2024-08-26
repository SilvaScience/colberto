#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  5 11:26:35 2024

@author: katiekoch
"""
from pathlib import Path
import matplotlib.pyplot as plt
from ctypes import *
import numpy as np

from src.drivers.stresing_camera import camera_settings
from src.drivers.stresing_camera import measurement_settings
from src.drivers.stresing_camera import stresing

# Intitalize stressing camera 
CAM = stresing()

use_blocking_call = True 
    #True = returns data when measurement is finsihed 
    #False = returns data immediatley 

CAM.measure(use_blocking_call)

sample = 10
block = 0
list_frame_buffer = CAM.get_data_one_frame(sample,block)

# Plot the frame
plt.plot(list_frame_buffer) #pixel number vs intensity 
plt.title('One Frame')
plt.show()

CAM.close()

