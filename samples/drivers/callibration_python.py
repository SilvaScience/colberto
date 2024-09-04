# -*- coding: utf-8 -*-
"""
Created on thursday june 11 16:29:03 2024

@author: Mathieu Desmarais

Code for the callibration of the SLM and to check the refresh rate of the SLM. 
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
from pathlib import Path
import sys
import csv
from sklearn.preprocessing import MinMaxScaler
########################################################################################################################
################    Oscilloscope  Keysight communication            ##############################################3##
######################################################################################################################

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.drivers.Oscilloscope_Keysight_DSOX1202A import OscilloscopeController



OscilloscopeController=OscilloscopeController()
OscilloscopeController.initialisation()

########################################################################################################################
##################### Importing the SLM class and the ImageGen class from the Functions_SLM file ####################### 
########################################################################################################################
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.Slm_Meadowlark_optics import SLM
from src.drivers.Slm_Meadowlark_optics import ImageGen

# Initiate the SLM class
slm = SLM()
Image=ImageGen()

#######################################################################################################################
#################### Creation of the SDK and extraction of the parameter ##############################################
#######################################################################################################################
# Call the constructor to create the Blink SDK
slm.create_sdk()
print("Blink SDK was successfully constructed")


height ,width, depth,RGB, isEightBitImage = slm.parameter_slm()
print("height:",height,"width:",width,"depth:",depth,"is8bit:",isEightBitImage)

slm.load_lut("c:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\19x12_8bit_linearVoltage.lut");




#######################################################################################################################################
#Parameter for the image generation (with the ImageClass)
pixels_per_stripe = 256
  # pixels per stripe
pixel_value_one = 0  # reference value. 
NumberDataPoints = 256 # Number of gray values
NumRegions = 1 # number of regions. For a global calibration, we can use 1. For a local calibration, we want to use more regions.
vertical = True # vertical or horizontal stripes


#Initialisation of the data array. In a first time we want to build an array that will contain the image height x width x BytesPerImage)
# Same thing for the plane wave correction,and the intensity data.
image = np.zeros((height,width,8),dtype=np.uint8)
wfc = np.zeros((height,width,8),dtype=np.uint8)
ai_intensities = np.zeros(NumberDataPoints)
grey_scale = np.zeros(NumberDataPoints)
#########################################################################################################################################



    #Here we do a loop on the number of gray values we want to test. There is 256 gray values. The idea is to generate a stripe 
    #pattern. The stripe that have pixel_value_one will be the reference stripe. The stripe that have pixel_value_two will be the
    #stripe that will change. The difference between the two stripe will cause a interference pattern that we can measure the intensity.
    # The change in the intensity is the result of the constructive and destructive interference. With this information we can
    # generate a lut calibration. 

for i in range(NumberDataPoints):
    print("Gray:", i)
    pixel_value_two = 255-i
    

    # Generate the stripe pattern
    #Image.generate_stripe(image.ctypes.data_as(POINTER(c_ubyte)), wfc.ctypes.data_as(POINTER(c_ubyte)), width, height, depth, pixel_value_one , pixel_value_two, pixels_per_stripe, vertical, 1)
    Image.generate_solid(image.ctypes.data_as(POINTER(c_ubyte)), wfc.ctypes.data_as(POINTER(c_ubyte)), width, height, depth, 255-i, 1);
    slm.write_image(image, isEightBitImage)
    if i==0:
        sleep(5)
    sleep(0.05)    
    average_voltage_str = oscilloscope.query(':MEASure:VAVerage?')
    b=float(average_voltage_str.strip()) #
    ai_intensities[i]=b                  #data process to have the good array format
    grey_scale[i]=i                      #
    #sleep(0.2)


oscilloscope.close()
slm.delete_sdk()

#####################################################################################################################################
#################### Intensity data logging in a CSV file ###########################################################################
#####################################################################################################################################

a=np.linspace(0,100,256) # Graph of the intensity in function of the gray scale
plt.figure()
plt.plot(a,ai_intensities)
plt.show()

# Normaliser ai_intensities de 0 à 1
scaler = MinMaxScaler()
ai_intensities_reshaped = ai_intensities.reshape(-1, 1)
normalized_ai_intensities = scaler.fit_transform(ai_intensities_reshaped).flatten()

# Combiner grey_scale et les valeurs normalisées
data = np.column_stack((grey_scale,ai_intensities))
data[:, 0] = data[:, 0].astype(int)

# Afficher les valeurs normalisées (facultatif)
#print(data[:, 0])
#print(data[:, 1])

# Spécifiez le chemin du fichier CSV
file_path = r"C:\Users\MathieuDesmarais\OneDrive - Universite de Montreal\Documents\GitHub\colberto\samples\drivers\Raw4.csv"

# Écrire les données dans le fichier CSV
with open(file_path, mode='w', newline='') as file:
    writer = csv.writer(file)
    # Écrire les données
    for row in data:
        writer.writerow([int(row[0]), row[1]])

print(f"CSV file has been written to {file_path}")
