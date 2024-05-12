# -*- coding: utf-8 -*-
"""
Created on Thu Nov  2 12:42:19 2023
@author: bulbula
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


# Load the DLL
# Blink_C_wrapper.dll, HdmiDisplay.dll, ImageGen.dll, freeglut.dll and glew64.dll
# should all be located in the same directory as the program referencing the
# library
cdll.LoadLibrary("C:\\Users\\NanoUltrafast2\\Desktop\AB\SLM_AB\Blink_C_wrapper")
slm_lib = CDLL("Blink_C_wrapper")

# # indicate that our images are RGB
# RGB = c_uint(1);
# is_eight_bit_image = c_uint(0);

# Call the constructor
slm_lib.Create_SDK();
print ("Blink SDK was successfully constructed");

# height = c_uint(slm_lib.Get_Height());
# width = c_uint(slm_lib.Get_Width());
# depth = c_uint(slm_lib.Get_Depth());
# bytpesPerPixel = 4; #RGBA

# Read an image from the files
ImageOne = imageio.imread('C:\\Users\\NanoUltrafast2\\Desktop\AB\SLM_AB\SLM1_f0.8_0.bmp')
ImageTwo = imageio.imread('C:\\Users\\NanoUltrafast2\\Desktop\AB\SLM_AB\SLM1_f0.5_120.bmp')
ImageThree = imageio.imread('C:\\Users\\NanoUltrafast2\\Desktop\AB\SLM_AB\SLM1_f0.2_240.bmp')

is_eight_bit_image = c_uint(1);
# Loop between our images
for x in range(6):

    slm_lib.Write_image(ImageOne.ctypes.data_as(POINTER(c_ubyte)), is_eight_bit_image);
    sleep(1.0); # This is in seconds
    slm_lib.Write_image(ImageTwo.ctypes.data_as(POINTER(c_ubyte)), is_eight_bit_image);
    sleep(1.0); # This is in seconds
    slm_lib.Write_image(ImageThree.ctypes.data_as(POINTER(c_ubyte)), is_eight_bit_image);
    sleep(1.0); # This is in seconds

# Always call Delete_SDK before exiting
slm_lib.Delete_SDK();
