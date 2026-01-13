#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 23 15:30:59 2025

@author: katiekoch
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from scipy.signal import savgol_filter, argrelextrema, find_peaks
import Functions as p2g

############  '''## Input file path ##''' #############
# 06052025_WL_Test4_13_26_32.h5

# 2025_11_03_Spectra_SLM_Calib_2scan_FYLA_450nm_750nm_14_22_28.h5

fn = r"Data_Files/2025_11_03_Spectra_SLM_Calib_2scan_FYLA_450nm_750nm_14_22_28.h5"

############  '''## Load Data & Process ##''' #############

[wave,spectra,Total_GreyScale_Vals] = p2g.load_data(fn)

GreyScale_Vals = np.unique(Total_GreyScale_Vals)
############  '''## Average Spectra from Multiple Scans ##''' #############
avg_spectrum = np.zeros(
    (len(wave), len(GreyScale_Vals)))  # set array size to average spectrum from diff scans
for j in range(len(GreyScale_Vals)):
    for i in range(len(Total_GreyScale_Vals)):
        if Total_GreyScale_Vals[i] == GreyScale_Vals[j]:
            avg_spectrum[:, j] = avg_spectrum[:, j] + spectra[:, i]

scan_num = len(Total_GreyScale_Vals) / len(GreyScale_Vals)
print('scan_num', scan_num)

avg_spectrum = avg_spectrum/scan_num

# avg_spectrum = spectra[:,1:] # only for Montreal Data_Set
# GreyScale_Vals = Total_GreyScale_Vals[1:]

############  '''## Plot: wavelength spectrum for all grayscale values ##''' #############
wave_xlim = [420, 760]

plt.figure()
plt.title("wavelengh spectrum for all greyscale value")  # (kept as in original)
plt.plot(wave, avg_spectrum)
plt.xlim([wave_xlim[0], wave_xlim[1]])
plt.xlabel('Wavelength (nm)')
plt.ylabel('Intensity (arb. u.)')
plt.show()

############  '''## Trim Spectra to Relevent Wavelength Range ##''' #############
wavelength_cutoff_1 = 250
print('#################################################################')
print('Low Wavelength Cutoff', wave[wavelength_cutoff_1])

wavelength_cutoff_2 = 1100
print('#################################################################')
print('High Wavelength Cutoff', wave[wavelength_cutoff_2])

trim_wave = wave[wavelength_cutoff_1:wavelength_cutoff_2]
trim_avg_spectrum = avg_spectrum[wavelength_cutoff_1:wavelength_cutoff_2,:]

# test plot
plt.figure()
plt.title("wavelengh spectrum for all greyscale value")  # (kept as in original)
plt.plot(trim_wave, trim_avg_spectrum)
plt.xlabel('Wavelength (nm)')
plt.ylabel('Intensity (arb. u.)')
plt.show()

############  '''## Plot: grayscale scans for all relevant wavelengths ##''' #############
plt.figure()
plt.title("grayscale spectrum for all wavelength value")  # (kept as in original)
for i in range(len(trim_wave)):
    plt.plot(GreyScale_Vals, trim_avg_spectrum[i, :])
    plt.xlabel('Grey value (0-255)')
    plt.ylabel('Intensity (arb. u.)')
plt.show()

############  '''## Select wavelength index and grayscale trim ##''' #############

cut = 480  # EN: wavelength selection (index in wave)
print('#################################################################')
print('Wavelegnth of cut', trim_wave[cut])
print('#################################################################')

idx1 = 0     # EN: trim grayscale options
idx2 = 255   # FR: rognage des options de niveaux de gris

# Common grayscale window for all wavelengths
g_vals = GreyScale_Vals[idx1:idx2]
yData  = trim_avg_spectrum[cut, idx1:idx2]

############  '''## Plot intensity vs grayscale (single wavelength) ##''' #############
# EN: Optional: restrict to one period by trimming grayscale range
# FR: Optionnel : restreindre à une période via le rognage des niveaux de gris
plt.figure()
plt.title("")
plt.plot(GreyScale_Vals[idx1:idx2], trim_avg_spectrum[cut, idx1:idx2], label=trim_wave[cut])
plt.xlabel('Grayscale Value')
plt.ylabel('Intensity')
plt.legend()
plt.show()

############  '''## Fit 5th-order poly for ONE wavelength ##''' #############
order = 5
prom_frac=0.08
dist_frac=1/4
savgol_window=11
savgol_polyorder=3

yData  = trim_avg_spectrum[cut, idx1:idx2]

#print("fit domain:", g_vals[idx1:idx2][0], g_vals[idx1:idx2][-1])

coeffs, res = p2g.fit_poly5_from_unwrap(
    g_vals, yData,
    order=order,
    do_plots=True,
    smooth_yData=False,
    index=i,
    wavelength=trim_wave[cut],
    # unwrap kwargs (tune if needed):
    prom_frac=prom_frac, dist_frac=dist_frac, savgol_window=savgol_window, 
    savgol_polyorder=savgol_polyorder
)

############  '''## Fit 5th-order poly for EACH wavelength and store (with helper) ##''' #############
order = 5
Nw = len(trim_wave)

# Coefficient matrix: (Nw, 6) -> [c5, c4, c3, c2, c1, c0]
coef_mat = np.full((Nw, order + 1), np.nan, dtype=float)
fit_ok = np.zeros(Nw, dtype=bool)

for i in range(Nw):
    yData = trim_avg_spectrum[i, idx1:idx2]

    # Unwrap + fit using the helper function
    coeffs, res = p2g.fit_poly5_from_unwrap(
        g_vals, yData,
        order=order,
        do_plots=False,
        smooth_yData=False,
        index=i,
        wavelength=trim_wave[i],
        # unwrap kwargs (tune if needed):
        prom_frac=prom_frac, dist_frac=dist_frac, savgol_window=savgol_window, 
        savgol_polyorder=savgol_polyorder
    )
        
    if coeffs is not None:
        coef_mat[i, :] = coeffs
        fit_ok[i] = True

print(f"Fitted {fit_ok.sum()} / {Nw} wavelengths.")

############  '''## Save CSV: wavelength + coefficients ##''' #############
# out = np.column_stack([trim_wave.reshape(-1, 1), coef_mat])
# header = "wavelength_nm,c5,c4,c3,c2,c1,c0"
# np.savetxt("poly5_coeffs_by_wavelength.csv", out, delimiter=",", header=header, comments="")
# print("Saved coefficients to poly5_coeffs_by_wavelength.csv")

############  '''## Optional visual check on an index (e.g., cut) ##''' #############
i = cut

if 0 <= i < Nw and fit_ok[i]:
    c5, c4, c3, c2, c1, c0 = coef_mat[i]
    poly5 = np.poly1d([c5, c4, c3, c2, c1, c0])
    phase_fit = poly5(g_vals)


    # Recompute unwrapped phase for plotting
    _, res_test = p2g.fit_poly5_from_unwrap(
        g_vals, trim_avg_spectrum[i, idx1:idx2],
        order=order, do_plots=False, smooth_yData=False, index=i, 
        wavelength=trim_wave[i],
        prom_frac=prom_frac, dist_frac=dist_frac, savgol_window=savgol_window, 
        savgol_polyorder=savgol_polyorder
    )
    
    phi_test = res_test['phi_unw']
    #print(phi_test)
    offset = np.round((phi_test[0] - phase_fit[0]) / (2 * np.pi))
    print(f"Offset difference: {offset} × 2π")

    if res_test is not None:
        phi_test = res_test['phi_unw']
        plt.figure()
        plt.title(f"λ = {trim_wave[i]:.1f} nm: unwrap + poly5 fit")
        plt.plot(g_vals, phi_test, 'k.', label='phi_unw')
        plt.plot(g_vals, phase_fit, '-', label=f'poly{order} fit', color='orange')
        plt.xlabel('Grayscale Value')
        plt.ylabel('Phase (rad)')
        plt.legend()
        plt.tight_layout()
        plt.show()

############  '''## Plot: polynomial coefficients vs wavelength ##''' #############
lam_ok = trim_wave[fit_ok]
coef_ok = coef_mat[fit_ok, :]  # shape: (Nok, 6) -> [c5, c4, c3, c2, c1, c0]

labels = ['c5', 'c4', 'c3', 'c2', 'c1', 'c0']
for j, lab in enumerate(labels):
    plt.figure()
    plt.plot(lam_ok, coef_ok[:, j], lw=1.8)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel(lab)
    plt.title(f'{lab} vs wavelength')
    plt.tight_layout()
    plt.show()


