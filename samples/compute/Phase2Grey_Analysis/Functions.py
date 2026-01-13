#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 24 12:16:27 2025

@author: katiekoch
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from scipy.signal import savgol_filter, argrelextrema, find_peaks

plt.rcParams["figure.figsize"] = [6,5]

def load_data(fn):
    
    """
    Parameters
    ----------
    fn : filepath for data

    Returns
    -------
    result : dict
        {
            'wave'   : wavelength array (np.ndarray),
            'spectra'  : spectrum array (np.ndarray),
            'Total_GreyScale_Vals': grayscale value array (np.ndarray),
        }
    """

    ############  '''## Load datasets and attributes ##''' #############
    with h5py.File(fn, 'r') as hdf:

        ls = list(hdf.keys())
        print('#################################################################')
        print('List of Data Sets in this file: \n', ls)

        data = hdf.get('spectra')
        data_set = np.array(data)

        param_set = hdf.get('parameter')
        param_set = np.array(param_set)

        # EN: keep a reference to 'spectra' dataset (not used differently later)
        # FR: on conserve la référence au dataset 'spectra' (usage inchangé)
        data = hdf.get('spectra')

        # EN: parameter names and wavelength axis (attributes)
        # FR: noms des paramètres et axe de longueur d'onde (attributs)
        # print(grp.attrs['parameter_keys'])
        grf = hdf['parameter']
        params = grf.attrs['parameter_keys']
        
        grp = hdf['spectra']
        wave = grp.attrs['xaxis']

    ############  '''## Locate "greyscale_val" index in parameter list ##''' #############
    try:
        # EN: Find the index where params == 'greyscale_val'
        # FR: Trouver l'indice où params == 'greyscale_val'
        # index = params.index('greyscale_val')
        index = np.where(params == 'greyscale_val')
        index = np.array(index)
        #idx_val = int(index[0])
        idx_val = int(index[0].item())
        print('#################################################################')
        print("String found at index", idx_val)
    except ValueError:
        print("String not found!")

    ############  '''## Build working arrays (grayscale & spectra) ##''' #############
    Total_GreyScale_Vals = param_set[idx_val, :]
    
    spectra = data_set
    
    return [wave,spectra,Total_GreyScale_Vals]


############  '''## Function: Manually Unwrap Phase (improved) ##''' #############
# EN: Derive a monotonic unwrapped phase from intensity oscillations for ONE wavelength trace.
# FR: Extraire une phase déroulée monotone à partir des oscillations d'intensité pour UNE longueur d'onde.
############  '''## Function: Manually Unwrap Phase (improved) ##''' #############
# EN: Derive a monotonic unwrapped phase from intensity oscillations for ONE wavelength trace.
# FR: Extraire une phase déroulée monotone à partir des oscillations d'intensité pour UNE longueur d'onde.

def unwrap_phase_from_intensity(
    g,
    y_raw,
    prom_frac=0.08,          # EN: fraction of signal span used for peak prominence | FR: fraction de la dynamique pour la proéminence
    dist_frac=1/6,           # EN: minimal peak distance as a fraction of len(g)     | FR: distance minimale entre pics en fraction de len(g)
    savgol_window=11,        # EN: Savitzky–Golay window length (must be odd)        | FR: fenêtre Savitzky–Golay (impair)
    savgol_polyorder=3,      # EN: Savitzky–Golay polynomial order                   | FR: ordre du polynôme Savitzky–Golay
    do_plots=False,
    smooth_yData=False,
    index=0,
    wavelength=None,                      # EN: show diagnostic plots                              | FR: afficher les graphes de contrôle
):
    """
    Parameters
    ----------
    g : np.ndarray
        EN: grayscale positions (shape: (Ng,))
        FR: positions des niveaux de gris (forme: (Ng,))
    y : np.ndarray
        EN: intensity at the selected wavelength (shape: (Ng,))
        FR: intensité à la longueur d'onde choisie (forme: (Ng,))
    prom_frac : float
        EN: fraction of (y.max - y.min) for peak prominence
        FR: fraction de (y.max - y.min) pour la proéminence des pics
    dist_frac : float
        EN: minimal distance between peaks as a fraction of len(g)
        FR: distance minimale entre pics en fraction de len(g)
    savgol_window : int
        EN: Savitzky–Golay window length (odd, <= len(g))
        FR: longueur de fenêtre Savitzky–Golay (impair, <= len(g))
    savgol_polyorder : int
        EN: Savitzky–Golay polynomial order (< window)
        FR: ordre du polynôme Savitzky–Golay (< fenêtre)
    do_plots : bool
        EN/FR: toggle diagnostic figures
    smooth_yData : bool
        EN/FR: toggle feature to smooth the yData (intensity vs. grayscale) 
        using the savgol_filter 

    Returns
    -------
    result : dict
        {
            'phi_unw'   : unwrapped phase (np.ndarray),
            'phi_base'  : base wrapped phase before smoothing (np.ndarray),
            'phi_smooth': smoothed wrapped phase (np.ndarray),
            'turns'     : turning points indices (np.ndarray),
            'imax'      : peaks indices (np.ndarray),
            'imin'      : troughs indices (np.ndarray),
            'span'      : total unwrapped span in radians (float)
        }
    """
    
    # print('#################################################################')
    # print('do_plots', do_plots)
    
    if smooth_yData:
        y = phi_smooth = savgol_filter(y_raw, savgol_window, savgol_polyorder)
    else:
        y = y_raw
    
    
    # ---------- EN: guards for Savitzky–Golay parameters ----------
    # ---------- FR: garde-fous pour les paramètres Savitzky–Golay ----------
    Ng = len(g)
    if savgol_window > Ng:
        savgol_window = Ng if Ng % 2 == 1 else Ng - 1
        savgol_window = max(savgol_window, savgol_polyorder + 2 if (savgol_polyorder + 2) % 2 == 1 else savgol_polyorder + 3)
    if savgol_window < 3:
        savgol_window = 3
    if savgol_window % 2 == 0:
        savgol_window += 1
    if savgol_polyorder >= savgol_window:
        savgol_polyorder = max(1, min(3, savgol_window - 2))

    # ---------- 1) données / data ----------
    # EN: raw intensity at λ=wave[cut] (or yData_Norm if preferred)
    # FR: intensité brute à λ=wave[cut] (ou yData_Norm si préféré)
    y_min, y_max = float(y.min()), float(y.max())

    # ---------- 2) robust peaks/troughs detection ----------
    # EN: ~8% of span; ~3 periods over 0–255 => distance ≈ len(g)/6
    # FR: ~8% de la dynamique; ~3 périodes sur 0–255 => distance ≈ len(g)/6
    prom = prom_frac * (y_max - y_min)
    dist = max(10, int(len(g) * dist_frac))

    imax, props_max = find_peaks(y,  prominence=prom, distance=dist)
    imin, props_min = find_peaks(-y, prominence=prom, distance=dist)

    # ---------- 3) turning points (max ∪ min) ----------
    # EN: sorted union, excluding edges
    # FR: union triée, bords exclus
    turns = np.sort(np.r_[imax, imin])
    if turns.size:
        turns = turns[(turns > 0) & (turns < len(g) - 1)]

    # ---------- 4) base wrapped phase (normalize -> arccos -> smooth) ----------
    # EN: normalize to [-1,1] then arccos
    # FR: normalisation vers [-1,1] puis arccos
    yn = (y - (y_min + y_max) / 2.0) * 2.0 / (y_max - y_min) if (y_max > y_min) else np.zeros_like(y)
    yn = np.clip(yn, -1.0, 1.0)
    phi_base   = np.arccos(yn)
    phi_smooth = savgol_filter(phi_base, savgol_window, savgol_polyorder)

    # ---------- 5) segmentation + mirroring + +π per half-period ----------
    # EN: force monotonicity segment-wise and add offset of π per half-period
    # FR: rendre chaque segment monotone et ajouter un décalage de π par demi-période
    edges = np.r_[0, turns, len(g)] if turns.size else np.array([0, len(g)])
    phi_unw = np.empty_like(phi_smooth)
    offset = 0.0
    for k in range(len(edges) - 1):
        s, e = int(edges[k]), int(edges[k + 1])
        seg = phi_smooth[s:e].copy()
        if seg.size == 0:
            continue
        # EN: make the segment increasing if needed
        # FR: rendre le segment croissant si nécessaire
        if seg[-1] < seg[0]:
            seg = np.pi - seg
        seg += offset
        phi_unw[s:e] = seg
        offset += np.pi  # EN: half-period -> +π | FR: demi-période -> +π

    # ---------- 6) sanity check ----------
    # EN: span in radians (≈ nb_half_periods * π) | FR: étendue en radians
    span = float(phi_unw.max() - phi_unw.min())
    print(f"Δφ ≈ {span:.3f} rad  (~ {span/np.pi:.2f} × π)")

    # ---------- Optional diagnostic plots ----------
    if do_plots:
        # (A) Intensity with peaks/troughs
        plt.figure()
        plt.title(f"Intensity vs Grayscale (peaks & troughs). Wavelength: {wavelength:.1f} nm")
        plt.plot(g, y_raw, lw=1.5, linestyle='--',label="Intensity-Raw")
        plt.plot(g, y, lw=1.5, label="Intensity")
        if imax.size:
            plt.plot(g[imax], y[imax], "o", ms=5, label="Peaks")
        if imin.size:
            plt.plot(g[imin], y[imin], "o", ms=5, label="Troughs")
        for t in (turns if turns.size else []):
            plt.axvline(g[t], ls="--", alpha=0.25)
        plt.xlabel("Grayscale Value")
        plt.ylabel("Intensity (arb. u.)")
        plt.legend()
        plt.tight_layout()
        plt.show()

        # (B) Wrapped phase: raw vs smoothed
        plt.figure()
        plt.title(f"Phase (wrapped): raw vs smoothed. Wavelength: {wavelength:.1f} nm")
        plt.plot(g, phi_base,   alpha=0.5, label="phi_base = arccos(norm I)" )
        plt.plot(g, phi_smooth, lw=2,      label="phi_smooth (SavGol)")
       
        for t in (turns if turns.size else []):
            plt.axvline(g[t], ls="--", alpha=0.2)
        plt.xlabel("Grayscale Value")
        plt.ylabel("Phase (rad)")
        plt.legend()
        plt.tight_layout()
        plt.show()

        # (C) Unwrapped phase guided by turning points
        plt.figure()
        plt.title(f"Phase (unwrapped) guided by peaks/troughs. Wavelength: {wavelength:.1f} nm")
        plt.plot(g, phi_unw, lw=2, label="phi_unwrapped (segment + π) wavelength[i]")
        for t in (turns if turns.size else []):
            plt.axvline(g[t], ls="--", alpha=0.25)
        plt.xlabel("Grayscale Value")
        plt.ylabel("Phase (rad)")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return {
        'phi_unw':    phi_unw,
        'phi_base':   phi_base,
        'phi_smooth': phi_smooth,
        'turns':      turns,
        'imax':       imax,
        'imin':       imin,
        'span':       span
    }

###############################################################################################################
###############################################################################################################
###############################################################################################################
###############################################################################################################
###############################################################################################################

############  '''## Function: unwrap + 5th-order polynomial fit ##''' #############
def fit_poly5_from_unwrap(
    g,
    y,
    order=5,
    do_plots=False,
    smooth_yData = False,
    index=None,
    wavelength=None,
    **unwrap_kwargs
):
    """
    Unwrap the phase from intensity oscillations and fit a 5th-order polynomial.

    Parameters
    ----------
    g : np.ndarray
        Grayscale values (x-axis).
    y : np.ndarray
        Intensity data for one wavelength (y-axis).
    order : int
        Polynomial order (default = 5).
    do_plots : bool
        If True, show diagnostic plots for unwrap and fit.
    smooth_yData : bool
        EN/FR: toggle feature to smooth the yData (intensity vs. grayscale) 
        using the savgol_filter
    index : int or None
        Optional index of the wavelength (used in warnings).
    wavelength : float or None
        Wavelength value (nm) for labeling and plots.
    **unwrap_kwargs :
        Extra arguments passed to unwrap_phase_from_intensity (e.g., prom_frac).

    Returns
    -------
    coeffs : np.ndarray or None
        Polynomial coefficients [cN,...,c0] if fit succeeded, else None.
    result : dict or None
        Full unwrap result (see unwrap_phase_from_intensity), else None.
    """
    
    # print('wavelength_array', wavelength)
    
    try:
        res = unwrap_phase_from_intensity(
            g, y,
            do_plots=do_plots,
            smooth_yData=smooth_yData,
            wavelength=wavelength,
            index=index,
            **unwrap_kwargs)
        phi = res['phi_unw']
    except Exception as e:
        import traceback
        print("### FULL TRACEBACK ###")
        traceback.print_exc()
        lbl = f" (λ={wavelength:.2f} nm)" if wavelength is not None else ""
        print(f"[WARN] unwrap failed at index={index}{lbl}: {e}")
        return None, None

    # Guard: enough points
    if len(g) < order + 1 or len(phi) < order + 1:
        lbl = f" (λ={wavelength:.2f} nm)" if wavelength is not None else ""
        print(f"[WARN] not enough points for polyfit at index={index}{lbl}")
        return None, res

    try:
        coeffs = np.polyfit(g, phi, order)
    except Exception as e:
        lbl = f" (λ={wavelength:.2f} nm)" if wavelength is not None else ""
        print(f"[WARN] polyfit failed at index={index}{lbl}: {e}")
        return None, res

    # Optional visual check
    if do_plots:
        polyN = np.poly1d(coeffs)
        phase_fit = polyN(g)

        plt.figure()
        title = "Unwrap + Poly5 fit"
        if wavelength is not None:
            title += f" (λ={wavelength:.1f} nm)"
        plt.title(title)
        plt.plot(g, phi, 'k.', label='phi_unw')
        plt.plot(g, phase_fit, '-', label=f'poly{order} fit')
        plt.xlabel('Grayscale Value')
        plt.ylabel('Phase (rad)')
        plt.legend()
        plt.tight_layout()
        plt.show()

    return coeffs, res

###############################################################################################################
###############################################################################################################
###############################################################################################################
###############################################################################################################
###############################################################################################################
