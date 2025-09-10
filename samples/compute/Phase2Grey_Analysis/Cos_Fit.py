#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 15:50:14 2025

@author: katiekoch
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from scipy.signal import savgol_filter, argrelextrema
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d

fn = '06052025_WL_Test4_13_26_32.h5'

with h5py.File(fn,'r') as hdf:
    
    ls = list(hdf.keys())
    print('List of Data Sets in this file: \n', ls)
    
    data = hdf.get('spectra')
    data_set = np.array(data)
    #print(data_set.shape)
    
    param_set = hdf.get('parameter')
    param_set = np.array(param_set)
    
    data = hdf.get('spectra')
    
    grp = hdf['spectra']
    
    grf = hdf['parameter']

    #print(grp.attrs['parameter_keys'])
    params = grf.attrs['parameter_keys']
    wave = grp.attrs['xaxis']
###############################################################################
try:
    #index = params.index('greyscale_val')
    index = np.where(params=='greyscale_val')
    index = np.array(index)
    idx_val = int(index[0])
    print("String found at index", idx_val)
except ValueError:
    print("String not found!")
###############################################################################
Total_GreyScale_Vals = param_set[idx_val,:]
GreyScale_Vals = np.unique(Total_GreyScale_Vals)

cut = len(params)
print(cut)    

spectra = data_set
###############################################################################
plt.plot(wave,spectra[:,1:])
plt.xlim([450,1100])
plt.xlabel('Wavelength (nm)')
plt.ylabel('Intensity (arb. u.)')
plt.show()

avg_spectrum = spectra[:,1:]
GreyScale_Vals = Total_GreyScale_Vals[1:]
###############################################################################
plt.figure()

for i in range(len(wave)):

    plt.plot(GreyScale_Vals,avg_spectrum[i,:])
    
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Intensity (arb. u.)')
    
plt.show()
###############################################################################
cut = 1000 #300
print(wave[cut])
###############################################################################

###############################################################################
'''## Plot intensity as a function of grayscle for one wavelength ##'''
###############################################################################
plt.plot(GreyScale_Vals,avg_spectrum[cut,:], label = wave[cut])
plt.xlabel('Grayscale Value')
plt.ylabel('Intensity')
plt.legend()
plt.show()

## trim grayscale options - only one period ##

idx1 = 1
idx2 = 250

idx1 = 1
idx2 = 180#180

plt.plot(GreyScale_Vals[idx1:idx2],avg_spectrum[cut,idx1:idx2], label = wave[cut])
plt.xlabel('Grayscale Value')
plt.ylabel('Intensity')
plt.legend()
plt.show()

###############################################################################
'''##     Normalize for ArcCos Range (-1, 1)    ##'''
###############################################################################
g_vals = GreyScale_Vals[idx1:idx2]
yData = avg_spectrum[cut,idx1:idx2]

yData_remove_avg = yData - (np.min(yData)+np.max(yData))/2
yData_Norm = yData_remove_avg*2/(np.max(yData_remove_avg)-np.min(yData_remove_avg))

plt.plot(g_vals,yData_Norm)#, label = wave[cut])
plt.xlabel('Grayscale Value')
plt.ylabel('Intensity')

plt.show()

###############################################################################
'''##     Fitting Routine - I(g) = A + Bcos(phi(g))    ##'''
###############################################################################

def cosine_model_linear(g, A, B, C, D):
    return A + B * np.cos(C* g + D)

def cosine_model(g, A, B, C0, C1, C2, C3, C4):
    
    phi_g = C0 + C1*g + C2*g**2 + C3*g**3 + C4*g**4
    
    return A + B * np.cos(phi_g)

greyscale = g_vals
intensity = yData_Norm

popt, _ = curve_fit(cosine_model, greyscale, intensity, p0=[0.8, 0.5, 0, np.pi/255, 0, 0, 0], maxfev=8000)
print(popt)

fit = cosine_model(greyscale, *popt)

plt.plot(greyscale,intensity, label = wave[cut])
plt.plot(greyscale, fit, '--')
plt.xlabel('Grayscale Value')
plt.ylabel('Intensity')
plt.legend()
plt.show()

phase = popt[3]*greyscale + popt[4]*greyscale**2 #+ popt[5]*greyscale**3 + popt[6]*greyscale**4
    
plt.plot(greyscale, phase)
plt.xlabel('Grayscale Value')
plt.ylabel('Phase (rad.)')
plt.legend()
plt.show()

###############################################################################
'''##     Fit to Fifth Order Polynomial   ##'''
###############################################################################
# phase = unwrapped_phase

order = 5
coeffs = np.polyfit(g_vals, phase, order)
poly5 = np.poly1d(coeffs)
phase_fit = poly5(g_vals)

plt.plot(g_vals, phase, 'ko', label='Manually Unwrapped Phase')
plt.plot(g_vals, phase_fit, 'r-', label='5th-order polynomial fit')
plt.xlabel('Grayscale Value')
plt.ylabel('Phase (rad)')
plt.legend()
plt.show()
