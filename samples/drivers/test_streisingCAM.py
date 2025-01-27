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
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.drivers.streising_camera import camera_settings
from src.drivers.streising_camera import measurement_settings
from src.drivers.streising_camera import streising

########### Path to the DLL file ############
folder_path = Path(__file__).resolve().parent.parent.parent #add or remove parent based on the file location

path_camera_dll = folder_path / "src" / "drivers" / "stresing" / "ESLSCDLL.dll"
path_camera_dll = str(path_camera_dll)

path_config = folder_path / "src" / "drivers" / "stresing" / "config_WFU.ini"
path_config = str(path_config)

# Intitalize stressing camera 
CAM = streising(path_config, path_camera_dll)

use_blocking_call = True
    #True = returns data when measurement is finsihed 
    #False = returns data immediatley 

CAM.measure(use_blocking_call)

sample = 5
block = 0
list_frame_buffer = CAM.get_data_one_frame(sample,block)
# Plot the frame
plt.plot(list_frame_buffer) #pixel number vs intensity 
plt.title('One Frame')
plt.show()

CAM.close()

