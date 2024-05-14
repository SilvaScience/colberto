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

import SLM_functions_KK as SLM

[height, width, depth, image_lib]=SLM.initialize_SLM()

center_x = c_uint(width.value//2);
center_y = c_uint(height.value//2);

################ Generating a new image - SLM Image Library #########################
width = width.value
height = height.value
depth = depth.value

# needed for testing purposes
RGB = c_uint(0);

test_grating = np.empty([width*height], dtype=np.uint8);

# print(np.shape(test_grating))
# print('---------------------')
# print(np.size(test_grating))
# print('---------------------')

WFC = np.empty([width*height], dtype=np.uint8);
#print(WFC.shape)

Period = 128 
increasing = 0 #0 or 1
horizontal = 0 #0 or 1

test = test_grating.ctypes.data_as(POINTER(c_ubyte))

image_lib.Generate_Grating(test_grating.ctypes.data_as(POINTER(c_ubyte)), WFC.ctypes.data_as(POINTER(c_ubyte)), 
                            width, height, depth, Period, increasing, horizontal, RGB);

# slm_lib.Write_image(test_grating.ctypes.data_as(POINTER(c_ubyte)), is_eight_bit_image);
# sleep(5.0)

SLM.display_SLM(test_grating)
sleep(3.0)

SLM.clear_SLM()

################ Generating a new image - Python #########################

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

[height, width, depth, image_lib]=SLM.initialize_SLM()

SLM.display_SLM(img)
sleep(5.0)

SLM.clear_SLM()

