# -*- coding: utf-8 -*-
"""
Created on  14 mai 2024
@author: Mathieu
"""
#########################################################################
############ Importation of the package #################################
#########################################################################
import os
import numpy as np
from ctypes import *
from scipy import misc
from time import sleep
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import imageio
import math as m

#Importation of the Class SLM in the slm.py file. This class contains all the functions of the
#CDLL library. it need to specify the path for the CDLL files. 
from Fonction_SLM import SLM
from Fonction_SLM import ImageGen

# Path to the DLL file
path_blink_c_wrapper = "C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\Blink_C_wrapper"
path_image_gen = "C:\\Program Files\\Meadowlark Optics\\Blink 1920 HDMI\\SDK\\ImageGen"
# Instantiate the SLM class
slm = SLM(path_blink_c_wrapper)
Image=ImageGen(path_image_gen)


#######################################################################################################################
#################### Creation of the SDK and extraction of the parameter ##############################################
#######################################################################################################################
# Call the constructor to create the Blink SDK
slm.Create_SDK()
print("Blink SDK was successfully constructed")

# Get the dimensions of the SLM

rgb=0
bit=1
height ,width, depth,RGB, isEightBitImage = slm.Parameter_SLM(rgb,bit)


#############################################################################################################################
###################### generation of a image with the SLM function ##########################################################
#########################################################################3###################################################
test_grating = np.empty([width*height], dtype=np.uint8);
WFC = np.empty([width*height], dtype=np.uint8);
Period = 128 
increasing = 0 #0 or 1
horizontal = 0 #0 or 1
Image.generate_grating(test_grating.ctypes.data_as(POINTER(c_ubyte)), WFC.ctypes.data_as(POINTER(c_ubyte)), 
                            width, height, depth, Period, increasing, horizontal, RGB);

##############################################################################################################################
############################## Write of the image ############################################################################
##############################################################################################################################

slm.Write_image(test_grating.ctypes.data_as(POINTER(c_ubyte)), isEightBitImage); # Write_image take 2 arguments. the first parameter is a 1D array of the image data. The second parameter
sleep(5.0)                                                                       # is 0 if a RGB array is pass and 1 otherwise.

############# Clear the SDK ##################################################################################################

slm.Delete_SDK()


############################################################################
################ Generating a new image - Python ###########################
############## Image generation code is from Esteban #######################
############################################################################
A = 2
d = 128

chirp = [0, 0, 0, 0] # 3 2, 1, 0 order  
#chirp = [100000, 0, 0, 0] ### adding chirp doesn't match up on SLM

coeff_wavepix = np.array([0.06313, 485])
w_c = 505
w_c_delay = 505

#taille = size
#taille = np.array([792, 596]) #GT SLM dimensions 
taille = np.array([1920, 1200])


#active = np.array([1, 792, 1, 792]) #GT SLM dimensions
active = np.array([1, 1920, 1, 1920])


micaslope = 0

end = len(chirp)-1
for i in range(len(chirp)):
    chirp[end-i] = chirp[end-i]*(1e-15)**i/m.factorial(i)
    
chirp_delay = np.array([chirp[end-1], 0])
chirp[end-1] = 0
chirp_mica = np.array([micaslope*1e-15, 0])


c=299792458 # Speed of light
A = A*np.pi
w_c=2*np.pi*c/(w_c*1e-9)
w_c_delay=2*np.pi*c/(w_c_delay*1e-9)

Image = []

#print(np.polyval(coeff_wavepix, 300))

if active[0]==1:
    w = 2*np.pi*c/(np.polyval(coeff_wavepix, 1)*1e-9)
    offset = np.polyval(chirp,(w-w_c))/(2*np.pi)
    offset = offset + np.polyval(chirp_delay, (w-w_c_delay))/(2*np.pi)
    image = A*np.remainder(1/d*np.arange(active[2]-1, active[3], 1)-offset, 1)
    image = np.append(np.append(np.zeros(active[2]-1), image), np.zeros(taille[0]-active[3]))

else:
    image=np.zeros(taille[0])

Image.append(image)

for i in np.arange(2, taille[1]+1, 1):
    if active[0] <= i <= active[1]:
        w = 2*np.pi*c/(np.polyval(coeff_wavepix, i)*1e-9)
        if micaslope != 0 and np.mod(i, 2) ==0:
            offset = np.polyval(chirp, (w-w_c))/(2*np.pi)
            offset = offset + np.polyval(chirp_mica, (w-w_c_delay))/(2*np.pi)
        else:
            offset=np.polyval(chirp,(w-w_c))/(2*np.pi)
            offset=offset+np.polyval(chirp_delay,(w-w_c_delay))/(2*np.pi)
        temp = A*np.remainder(1/d*np.arange(active[2]-1, active[3], 1)-offset, 1)
        temp = np.append(np.append(np.zeros(active[2]-1), temp), np.zeros(taille[0]-active[3]))
    else:
        temp = np.zeros(taille[0])
    Image.append(temp)

Image = np.transpose(np.array(Image))

ax1 = plt.contourf(Image)
ax1.axes.get_xaxis().set_visible(False)
ax1.axes.get_yaxis().set_visible(False)

plt.show()
# end of code from Esteban
############################################################################

############## Sending Image to SLM #######################

# reshaping to a 1D array to send to SLM 
data = np.reshape(Image,(1200*1920,)) 

# changing data type from np.float64 to np.uint8
data = data.astype(np.float64) / np.max(data) # normalize the data to 0 - 1
data = 255 * data # Now scale by 255
img = data.astype(np.uint8)

# print(np.shape(img))
# print('---------------------')
# print(np.size(img))

# Call the constructor to create the Blink SDK
slm.Create_SDK()
print("Blink SDK was successfully constructed")

# Get the dimensions of the SLM
height = slm.Get_Height()
width = slm.Get_Width()
depth = slm.Get_Depth()

slm.Write_image(img.ctypes.data_as(POINTER(c_ubyte)),c_uint(1))
sleep(5.0)

slm.Delete_SDK();
