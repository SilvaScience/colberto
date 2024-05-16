# -*- coding: utf-8 -*-
"""
Created on Mon May 13 16:29:03 2024

@author: NanoUltrafast2
"""

## testing SLM functions ##

import os
import numpy as np
from ctypes import *
from scipy import misc
from time import sleep
import ctypes
import math as m
import matplotlib.pyplot as plt
from scipy.constants import pi
from scipy.signal import sawtooth

import Functions_SLM_KK as SLM

#Importation of the Class SLM in the slm.py file. This class contains all the functions of the
#CDLL library. it need to specify the path for the CDLL files. 
from Fonction_SLM import SLM
from Fonction_SLM import ImageGen

#%%
# Path to the DLL file
path_blink_c_wrapper = "C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\Blink_C_wrapper"
path_image_gen = "C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\ImageGen"

# Initiate the SLM class
slm = SLM(path_blink_c_wrapper)
Image=ImageGen(path_image_gen)

# Call the constructor to create the Blink SDK
slm.Create_SDK()
print("Blink SDK was successfully constructed")

# Get the dimensions of the SLM
height = slm.Get_Height()
width = slm.Get_Width()
depth = slm.Get_Depth()

RGB = c_uint(0)
isEightBitImage = c_uint(1)

################ Generating a new image - SLM Image Library ###################

grating = np.empty([width*height], dtype=np.uint8);

WFC = np.empty([width*height], dtype=np.uint8);

Period = 128 
increasing = 0 #0 or 1
horizontal = 0 #0 or 1

## using image class to generate grating ##
Image.generate_grating(grating.ctypes.data_as(POINTER(c_ubyte)), WFC.ctypes.data_as(POINTER(c_ubyte)), 
                            width, height, depth, Period, increasing, horizontal, RGB);

grating_img = grating.ctypes.data_as(POINTER(c_ubyte))

slm.Write_image(grating_img, isEightBitImage);
sleep(1.0)

#slm.Delete_SDK()

################### Generating a new image - Python ###########################

######## Image generation code is from Felix (beams.py in Git) ################
###############################################################################
def generate_1Dgrating(amplitude,period,phase,num):
        '''
            Generates a sawtooth pattern for Diffraction-based spatiotemporal pulse shaping
            input:
                amplitude: (float) number between 0 and 1 setting the amplitude of the grating to amplitude*2*pi
                period: period of the sawtooth pattern in units of pixels
                phase: phase to be imparted on the diffracted beam (see eq. 13 of Turner et al. Rev. Sci. Instr. 2011)
                num: the number of pixels in the sawtooth pattern  
        '''
        indices=np.arange(num)
        offset=phase/(2*pi)*period
        y=amplitude*sawtooth(2*pi*(indices-offset)/period,width=0) % 2*pi
        return y

###############################################################################

A = 1
period = 128
phase = 0
num = slm.Get_Size() #new function I added to SLM class Mathieu created

grating_pattern = generate_1Dgrating(A,period,phase,num)

# reshaping to a 1D array to a 2D array to view image in python
data = np.reshape(grating_pattern,(1200,1920)) 

data = np.transpose(data)

ax1 = plt.contourf(data)
ax1.axes.get_xaxis().set_visible(False)
ax1.axes.get_yaxis().set_visible(False)

plt.show()
###############################################################################

####################### Sending Image to SLM ##################################

# generate 1D grating already produces 1D array so no need to reshape just relabeling
data = grating_pattern 

# changing data type from np.float64 to np.uint8
# need to phase to greyscale calibration file to make this conversion accurate
# using normalization method for now - just for testing purposes 

data = data.astype(np.float64) / np.max(data) # normalize the data to 0 - 1
data = 255 * data # Now scale by 255
img = data.astype(np.uint8)

img = img.ctypes.data_as(POINTER(c_ubyte))

slm.Write_image(img ,isEightBitImage)
sleep(1.0)

slm.Delete_SDK()
