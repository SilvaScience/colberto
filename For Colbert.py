# -*- coding: utf-8 -*-
"""
Created on Tue Oct  5 09:45:45 2021

@author: esteb
"""
import numpy as np
import math as m
import matplotlib.pyplot as plt

A = 2
d = 10
chirp = [0, 0, 0, 0]
coeff_wavepix = np.array([0.06313, 485])
w_c = 510
w_c_delay = 560
taille = np.array([596, 792])
active = np.array([1, 792, 1, 792])
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

plt.contourf(Image)
