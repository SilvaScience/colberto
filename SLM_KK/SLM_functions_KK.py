# -*- coding: utf-8 -*-
"""
Created on Mon May 13 15:06:04 2024

@author: NanoUltrafast2
"""


from ctypes import *
import ctypes


def initialize_SLM():

    ##### Query DPI Awareness #####
    awareness = ctypes.c_int()
    errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
    #print(awareness.value)

    ##### Set DPI Awareness #####
    # the argument is the awareness level, which can be 0, 1 or 2:for 1-to-1 pixel control I seem to need it to be non-zero 
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)

    ##### Open Library ##### 
    cdll.LoadLibrary("C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\Blink_C_wrapper")
    # will need to adjust path 
    global slm_lib
    slm_lib = CDLL("Blink_C_wrapper")

    ##### Open Image Library ##### probably won't need this for COLBERT
    cdll.LoadLibrary("C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\ImageGen")
    # will need to adjust path
    #global image_lib
    image_lib = CDLL("ImageGen")

    ##### Indicate that images are RGB #####
    # shouldn't need RGB for COLBERT will make array unnecessarily large
    RGB = c_uint(1); # 1920 x 1200 x 3
    
    global eight_bit
    eight_bit = c_uint(1); # 1920 x 1200

    ##### Open Image Library #####
    slm_lib.Create_SDK();
    print ("Blink SDK was successfully constructed");


    height = c_uint(slm_lib.Get_Height());
    width = c_uint(slm_lib.Get_Width());
    depth = c_uint(slm_lib.Get_Depth());
    #bytpesPerPixel = 4; #RGBA
    
    ##### Load LUT file #####
    success = 0;
    if (height.value == 1200)and(depth.value == 8):
        slm_lib.Load_lut("C:\\LUT Files\\19x12_8bit_linearVoltage.lut");
        success = 1
        
    if success > 0: 
        print ("LoadLUT Successful")	
    else:
        print("LoadLUT Failed")
        
    return height, width, depth, image_lib 
    #image lib needed for testing purposes - dont think we will need the image library for COLBERT        
        
def display_SLM(array):
    ##### Loads Image to the SLM #####
        # takes two parameters:
            #parameter 1 =  1D 8-bit array of image data that has 1920*1200 elements
            #parameter 2 = 1 (unless RGB is used then 0)
    slm_lib.Write_image(array.ctypes.data_as(POINTER(c_ubyte)),eight_bit)
    
def clear_SLM():
    ##### Closes Communication with the SLM #####
    slm_lib.Delete_SDK();
    print('Finished')
    
