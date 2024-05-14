# -*- coding: utf-8 -*-
"""
Created on  14 mai 2024
@author: Mathieu
"""
import os
import numpy
from ctypes import *
from scipy import misc
from time import sleep
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import imageio





################################ MAKE SURE THE WINDOW SHOWS UP IN THE WRITE PLACE FOR THE DPI SETTINGS#############
# Query DPI Awareness (Windows 10 and 8)
import ctypes
awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
print(awareness.value)

# Set DPI Awareness  (Windows 10 and 8)
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
# the argument is the awareness level, which can be 0, 1 or 2:
# for 1-to-1 pixel control I seem to need it to be non-zero (I'm using level 2)

# Set DPI Awareness  (Windows 7 and Vista)
success = ctypes.windll.user32.SetProcessDPIAware()
# behaviour on later OSes is undefined, although when I run it on my Windows 10 machine, it seems to work with effects identical to SetProcessDpiAwareness(1)
#######################################################################################################################



#Importation of the Class SLM in the slm.py file. This class contains all the functions of the
#CDLL library. it need to specify the path for the CDLL files. 
from slm_test import SLM

# Path to the DLL file
path_name = "C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\Blink_C_wrapper"
# Instantiate the SLM class
slm = SLM(path_name)

# Load the ImageGen DLL it's for the image generation. 
cdll.LoadLibrary("C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\ImageGen")
image_lib = CDLL("ImageGen")


#######################################################################################################################

# Call the constructor to create the Blink SDK
slm.Create_SDK()
print("Blink SDK was successfully constructed")

# Get the dimensions of the SLM
height = slm.Get_Height()
width = slm.Get_Width()
depth = slm.Get_Depth()
bytesPerPixel = 4  # RGBA
center_x = width / 2
center_y = height / 2
RGB = c_uint(1)
isEightBitImage = c_uint(0)

# Create numpy arrays to hold the images
ImageOne = numpy.empty([width * height * bytesPerPixel], numpy.uint8, 'C')
ImageTwo = numpy.empty([width * height * bytesPerPixel], numpy.uint8, 'C')

# Create a blank vector to hold the wavefront correction
WFC = numpy.empty([width * height * bytesPerPixel], numpy.uint8, 'C')

# Generate phase gradients
image_lib.Generate_Stripe(ImageOne.ctypes.data_as(POINTER(c_ubyte)), WFC.ctypes.data_as(POINTER(c_ubyte)), width, height, depth, 0, 100, 5, RGB)

isEightBitImage = c_uint(1)
# Loop between our images
for x in range(2):
    slm.Write_image(ImageOne.ctypes.data_as(POINTER(c_ubyte)), isEightBitImage)
    sleep(1.0)  # This is in seconds

# Always call Delete_SDK before exiting
slm.Delete_SDK()

