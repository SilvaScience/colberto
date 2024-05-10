# -*- coding: utf-8 -*-
"""
Created on Mon Oct  4 10:24:28 2021

@author: Esteban Rojas Gatjens
"""

# Importing the packages
import numpy as np
import math as m
import numpy.matlib as npm
from scipy.interpolate import interp1d


##############################################################################
def read_file(path):
    return np.loadtxt(path, delimiter="\t")


##############################################################################
##############################################################################
# FUNCTIONS NEEDED FOR APPLY
##############################################################################
##############################################################################

def Apply_and_show(phase2gs_image, deform_comp_image, dispersion_comp, 
                   grating_amplitude, user_act_region, g_period, w_c_delay,  
                   deform_comp,micaslope_arr, coeff_wavepix, user_chirp,
                   w_c_user, user_beampos, 
                    SLM_height, SLM_width):
    
    Output = make_image_with_wavepixcal(user_act_region, micaslope_arr, 
                                        grating_amplitude, g_period, 
                                        coeff_wavepix, user_chirp, w_c_delay, 
                                        w_c_user, user_beampos, SLM_height, 
                                        SLM_width)
    return Output

def make_image_with_wavepixcal(user_act_region, micaslope_arr, grating_amplitude, 
                               g_period, coeff_wavepix, user_chirp, w_c_delay, 
                               w_c_user, user_beampos, SLM_height, 
                               SLM_width):
    
    taille = np.array(beams_2_taille(user_beampos, SLM_height, SLM_width))
    Active = np.array(user_act_region)
    micaslope = micaslope_arr
    A = np.array(grating_amplitude, dtype=float)
    d = float(g_period)
    chirp = user_chirp
    w_c_user = float(w_c_user)
    w_c_delay = float(w_c_delay)
    
    # Pulse 1
    P1 = generate_phasegrating_image(micaslope[0], A[0], d, chirp[0], 
                                     coeff_wavepix[0], w_c_user, 
                                     taille[0], Active[0], w_c_delay)
    P2 = generate_phasegrating_image(micaslope[1], A[1], d, chirp[1],
                                     coeff_wavepix[1], w_c_user, 
                                     taille[1], Active[1], w_c_delay)
    P3 = generate_phasegrating_image(micaslope[2], A[2], d, chirp[2], 
                                     coeff_wavepix[2], w_c_user, 
                                     taille[2], Active[2], w_c_delay)
    P4 = generate_phasegrating_image(micaslope[3], A[3], d, chirp[3], 
                                     coeff_wavepix[3], w_c_user, 
                                     taille[3], Active[3], w_c_delay)
    
    Image = np.append(np.append(np.append(P1, P2, axis=0), P3, axis=0),
                      P4, axis=0)
    return Image

def beams_2_taille(user_beampos, SLM_height, SLM_width):
    beam1 = np.array([user_beampos[0], SLM_width])
    beam2 = np.array([user_beampos[1]-user_beampos[0], SLM_width])
    beam3 = np.array([user_beampos[2]-user_beampos[1], SLM_width])
    beam4 = np.array([SLM_height-user_beampos[2], SLM_width])
    return [beam1, beam2, beam3, beam4]

def generate_phasegrating_image(micaslope, A, d, chirp, coeff_wavepix, 
                                w_c, taille, active, w_c_delay):
    c=299792458 # Speed of light
    end = len(chirp)-1
    chirp = np.longdouble(np.array(chirp))
    active = np.array(active)
    taille = np.array(taille)
    taille = taille.astype(int)
    active = active.astype(int)
    for i in range(len(chirp)):
        chirp[end-i] = (chirp[end-i]*(1e-15)**i)/m.factorial(i)
        
    chirp_delay = np.array([chirp[end-1], 0])
    chirp[end-1] = 0
    A = A*np.pi
    w_c=2*np.pi*c/(w_c*1e-9)
    w_c_delay=2*np.pi*c/(w_c_delay*1e-9)
    
    if active[0]==1:
        w = 2*np.pi*c/(np.polyval(coeff_wavepix, 1)*1e-9)
        offset = np.polyval(chirp,(w-w_c))/(2*np.pi)
        offset = offset + np.polyval(chirp_delay, (w-w_c_delay))/(2*np.pi)
        image = A*np.remainder(1/d*np.arange(active[2], active[3], 1)-offset, 1)
        image = np.append(np.append(np.zeros(active[2]), image),
                          np.zeros(taille[0]-(active[3])))
    else:
        image=np.zeros(taille[0])
    
    Image = [list(image)]
    
    for i in np.arange(2, taille[1]+1, 1):
        if active[0] <= i <= active[1]:
            w = 2*np.pi*c/(np.polyval(coeff_wavepix, i)*1e-9)
            offset=np.polyval(chirp,(w-w_c))/(2*np.pi)
            offset=offset+np.polyval(chirp_delay,(w-w_c_delay))/(2*np.pi)
            temp = A*np.remainder(1/d*np.arange(active[2]-1, active[3], 1)-offset, 1)
            temp = np.append(np.append(np.zeros(active[2]-1), temp), 
                             np.zeros(taille[0]-(active[3])))
        else:
            temp = np.zeros(taille[0])
        Image.append(list(temp))
    Image = transpose(Image)
    return Image

def transpose(A):
    n_columns = len(A)
    n_rows = len(A[0])
    A_new = np.zeros((n_rows, n_columns))
    for i in range(len(A)):
        for j in range(len(A[0])):
            A_new[j][i] = A[i][j]
    return A_new

def phase_2_grey_scale(Image, phase2gs_image):
    Image = np.array(Image)
    Image = np.remainder(Image, 2*np.pi)
    phase2gs_image = np.array(phase2gs_image)
    Image_grey_scale = Image*phase2gs_image
    return Image_grey_scale

##############################################################################
##############################################################################
# FUNCTIONS FOR FITTING WAVE2PIX
##############################################################################
##############################################################################

def fit_wave2pix(A, wave, pix, deg, l, r):
    A = np.array(A)
    A = A - A[-1,:]
    size = len(pix)
    wmax=[]
    for Ai in A:    
        index = abs(Ai-max(Ai)).argmin()
        wmax.append(wave[index])
    coeff = np.polyfit(pix[l:size-r], wmax[l:size-r], deg)     
    return coeff

def eval_fit(coeff, pix, wave, A, l, r):
    
    A = np.array(A)
    A = A - A[-1,:]
    wmax=[]
    for Ai in A:    
        index = abs(Ai-max(Ai)).argmin()
        wmax.append(wave[index])
    size = len(pix)
    wmax = np.array(wmax)
    pix = pix[l:size-r]
    wmax = wmax[l:size-r]
    fit = np.polyval(coeff, pix)
    return np.array([pix, fit, wmax])

##############################################################################
##############################################################################
# FUNCTIONS FOR COMPRESSION FITTING
##############################################################################
##############################################################################

def Chirp_scan_fit(Data, wavelength,chirp, w_h, w_l, w_c, snr, l, r, deg):
        #Data, wavelength, chirp, w_h, w_l, rm_l, rm_r, snr):
    [wmax, chirp_out] = Chirp_processing(Data, wavelength,w_h, w_l, w_c, chirp, snr)
    coeff = np.polyfit(chirp_out, wmax, deg)
    return coeff

def eval_chirp_fit(Data, wavelength,w_h, w_l, w_c, chirp, snr, l, r, coeff):
    [wmax, chirp_out] = Chirp_processing(Data, wavelength,w_h, w_l, w_c, chirp, snr)
    fit = np.polyval(coeff, chirp_out)
    return np.array([chirp_out, wmax, fit])

def Chirp_processing(Data, wavelength,w_h, w_l, w_c, chirp, snr, l, r):
    c = 299792458
    Data = np.array(Data)
    wavelength = np.array(wavelength)
    index_l = (abs(wavelength-w_l)).argmin()
    index_h = (abs(wavelength-w_h)).argmin()
    wavelength = wavelength[index_l:index_h]
    Data = Data[:,index_l:index_h]
    Data = Data - np.min(Data) # Remove background
    noise = np.average(Data[-1,:]) # Noise on the last scan  
    frequency = 2*np.pi*c*(1e-9)*((2/wavelength)-(1/w_c))
    wmax = []
    chirp_out = []
    for i in range(len(Data)):    
        if max(Data[i])> snr*noise: 
            index = abs(Data[i]-max(Data[i])).argmin()
            wmax.append(frequency[index])
            chirp_out.append(chirp[i])
    size = len(chirp_out)
    return wmax[l:size-r], chirp_out[l:size-r]

##############################################################################
##############################################################################
# FUNCTIONS FOR PHASE2GS_IMAGE AND DEFORM COMP
##############################################################################
##############################################################################

# DEFORMATION CORRECTION
def deformation_correction(path, coeff_wavepix, beam_pos):
    Coeff_1 = import_deform_coeff(path+"coeff_deform_slm_2021_1.txt")
    Coeff_2 = import_deform_coeff(path+"coeff_deform_slm_2021_2.txt")
    Coeff_3 = import_deform_coeff(path+"coeff_deform_slm_2021_3.txt")
    Coeff_4 = import_deform_coeff(path+"coeff_deform_slm_2021_4.txt")
    
    deform = np.zeros((len(Coeff_1), len(np.transpose(Coeff_1))))
    
    I = range(1,len(np.transpose(Coeff_1))+1)

    for k in range(1, len(coeff_wavepix)+1):
        for i in range(1,len(np.transpose(Coeff_1))+1):
            if k == 1:
                Wavelength = np.polyval(coeff_wavepix[0], I)
                for j in range(1, len(Coeff_1)+1):
                    squeeze = np.array([Coeff_1[j-1,i-1],Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]])
                    deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1])
        
            elif k == len(coeff_wavepix):
                Wavelength = np.polyval(coeff_wavepix[k-1], I)
                for j in range(beam_pos[k-2]+1, len(Coeff_1)):
                    squeeze = np.array([Coeff_1[j-1,i-1],Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]]) 
                    deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1]) 
            else: 
                Wavelength = np.polyval(coeff_wavepix[k-1], I)
                for j in range(beam_pos[k-2]+1, beam_pos[k-1]):
                    squeeze = np.array([Coeff_1[j-1,i-1], Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]]) 
                    deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1])
                    
    deform = np.unwrap(deform, axis=1)
    return deform

# Phase_2gs_image
def phase_2gs_image(path, size, coeff_wavepix, beam_pos=[150, 300, 450]):
    
    [X, Y] = import_phase2gs_calib_files(path)
    func = interp1d(X, Y, kind='cubic')
    image_gs=np.zeros((size[0], size[1]))
    
    for k in range(1, len(coeff_wavepix)+1):
        if k==1:
            wave = np.polyval(coeff_wavepix[0], np.arange(1, size[1]+1))
            wave[np.where(wave>700)] = 700*np.ones(len(np.where(wave>700)))
            image_gs=npm.repmat(func(wave), beam_pos[0],1)

        elif k == (len(coeff_wavepix)):
            wave = np.polyval(coeff_wavepix[k-1], np.arange(1, size[1]+1))
            wave[np.where(wave>700)] = 700*np.ones(len(np.where(wave>700)))
            image_gs = np.append(image_gs, npm.repmat(func(wave), size[0]-beam_pos[k-2],1), axis=0)
            
        else:
            wave = np.polyval(coeff_wavepix[k-1], np.arange(1, size[1]+1))
            wave[np.where(wave>700)] = 700*np.ones(len(np.where(wave>700)))
            image_gs = np.append(image_gs, npm.repmat(func(wave), beam_pos[k-1]-beam_pos[k-2],1), axis=0)
            
    return image_gs

##############################################################################
# Auxiliar functions
##############################################################################
def import_deform_coeff(data_path, skip_lines=0):
    with open(data_path, 'r') as file:
        lines = file.readlines()[skip_lines:]
        Array = []
        for line in lines:
            Array.append(np.array([float(i) for i in line.split("\t")]))
    return np.matrix(Array)

def f_polyval(p, x):
    return p[3]+p[2]*x+p[1]*x**2+p[0]*x**3

def import_phase2gs_calib_files(path, skip_lines=0):
    pp_x = path + "PP_X.txt" 
    with open(pp_x, 'r') as file:
        lines = file.readlines()[skip_lines:]
        X = np.array([float(i) for i in lines[0].split("\t")])
    
    pp_y = path + "PP_Y.txt" 
    with open(pp_y, 'r') as file:
        lines = file.readlines()[skip_lines:]
        Y = np.array([float(i) for i in lines[0].split("\t")])
    return X, Y
##############################################################################



#TEST
path = "C:\\Users\\labuser\\Documents\\Data\\Calibration files\\COLBERT\\SLM phase to greyscale\\"