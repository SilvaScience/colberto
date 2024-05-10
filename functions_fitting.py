# -*- coding: utf-8 -*-
"""
Created on Wed Jan 19 14:57:47 2022

@author: esteb
"""

import numpy as np
import math as m
import numpy.matlib as npm
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

data = "FORTESTING/Chirp_Scan_beam4.txt"

def import_scan(data, skip_lines=0):
    with open(data, 'r') as file:
        lines = file.readlines()[skip_lines:]
        size = len(lines)
        
        wl = np.array(lines[-1].split("\t"))
        wl = wl.astype(np.float)
        
        chirp = np.array(lines[-2].split("\t"))
        chirp = chirp[:size-3].astype(np.float)
        
        Matrix = []
        for line in lines[:size-3]: 
            Matrix.append(np.array(line.split("\t")))
        
        Matrix = np.array(Matrix)
        Matrix = Matrix.astype(np.float)
        
    return Matrix, wl, chirp

[Matrix, wl, chirp] = import_scan(data)

#plt.contourf(chirp, wl, np.transpose(Matrix))
#plt.show()

wl_max = 340
wl_min = 280
SNR = 20
w_c = 620
c=299792458
order = 4

max_indx = abs(wl-wl_max).argmin()
min_indx = abs(wl-wl_min).argmin()

# Restrict the wavelength range
wl = wl[min_indx: max_indx]
Matrix = Matrix[:,min_indx: max_indx]

# Substract background
Matrix = Matrix-np.min(Matrix)

#Find amplitude of the noise
noise= np.average(Matrix[:,-1])

plt.contourf(chirp, wl, np.transpose(Matrix))
plt.show()

frequency = 2*np.pi*c*1e9*((1/(2*wl))-(1/w_c))
# frequency_r=2*pi*c*1e9*(0.5./wavelength(max(image_in)>coeff*noise)-1./lambdac);

x = []
y = []
for i in range(len(wl)):
    if max(Matrix[:,i])>SNR*noise:
        indx_max = abs(Matrix[:,i]- max(Matrix[:,i])).argmin()
        y.append(chirp[indx_max])
        x.append(frequency[i])

coeff = np.polyfit(x, y, order)
test=np.polyval(coeff,x)

plt.plot(x, y, marker=".", linestyle="none")
plt.plot(x, test, marker=".", linestyle="none")

print(coeff)
end = len(coeff)-1
for i in range(len(coeff)):
    coeff[end-i] = ((1e15)**i)*coeff[end-i]*m.factorial(i)

print(coeff)







