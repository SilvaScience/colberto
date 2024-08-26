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
from scipy.signal import find_peaks

from Functions_Stressing_KK import camera_settings
from Functions_Stressing_KK import measurement_settings
from Functions_Stressing_KK import stresing

from calibration import Calibration
from Functions_SLM_KK import SLM

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

Data = np.array(list_frame_buffer)
pixels = np.arange(1024)

plt.plot(pixels,Data)
plt.show()

CAM.close()

#%%
np.savetxt('mercury_lamp_calib',[pixels,Data])


#%%

# cal=Calibration(SLM,stressing)

# threshold = 6000
# deg = 3
# wavelength_calib = cal.camera_calib(Data, threshold, deg, pixels)

# plt.plot(wavelength_calib,Data-5000)
# plt.xlim([300,700])
# plt.ylim([0,10000])
# plt.show()

