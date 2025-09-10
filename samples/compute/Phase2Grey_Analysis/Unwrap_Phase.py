#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  3 15:44:01 2025

@author: katiekoch
"""
import h5py
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from scipy.signal import savgol_filter, argrelextrema

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
cut = 300 #300
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

# idx1 = 75
# idx2 = 135

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
'''##     Compute Phase - ArcCos of Intensity Profile    ##'''
###############################################################################
phi_base = np.arccos(yData_Norm)

phi_smooth = savgol_filter(phi_base, window_length=11, polyorder=3)

plt.plot(g_vals,phi_base, label = 'phase')
plt.plot(g_vals,phi_smooth, label = 'smoothed phase')
plt.xlabel('Grayscale Value')
plt.ylabel('Phase (rad.)')
plt.legend()
plt.show()

# phase_unwrap = np.unwrap(phi_base)

# plt.plot(g_vals,phi_base, label = 'phase')
# plt.plot(g_vals,phase_unwrap, label = 'unwrap')
# plt.xlabel('Grayscale Value')
# plt.ylabel('Phase (rad.)')
# plt.legend()
# plt.show()

###############################################################################
'''##     Manually Unwrap Phase   ##'''
###############################################################################
dphi = np.gradient(phi_smooth)

plt.plot(g_vals,dphi)
plt.xlabel('Grayscale Value')
plt.ylabel('Phase (rad.)')
plt.show()

threshold = 3  # define threshold for jump
wrap_locs = np.where(dphi < threshold)[0] # array of positons where the phase jumps

# Step 4: Manually unwrap phase
unwrapped_phase = phi_base.copy()
offset = 0 # keeps track of cmulative phase added due to unwrapping

for i in range(1, len(unwrapped_phase)):
    if i in wrap_locs:
        offset += np.pi #adds pi to the offset 
    unwrapped_phase[i] += offset # adds the current cumulative offset to the phase value at that point

plt.plot(g_vals, phi_base, label='Measured Phase (wrapped)', alpha=0.7)
plt.plot(g_vals, unwrapped_phase, label='Manually Unwrapped Phase', linewidth=2)
plt.legend()
plt.xlabel('Grayscale Value')
plt.ylabel('Phase (rad)')
plt.show()

###############################################################################
'''##     Fit to Fifth Order Polynomial   ##'''
###############################################################################
phase = unwrapped_phase

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
