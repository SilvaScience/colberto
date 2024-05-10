# -*- coding: utf-8 -*-
"""
Created on Sat Jul  3 19:29:36 2021

@author: Esteban Rojas Gatjens

These functions correspond to direct translations from the Matlab codes 
implemented in the Colbert labview code.

"""
import numpy as np
import numpy.matlib as npm
from scipy.interpolate import interp1d

##############################################################################
# Main funcitons
##############################################################################

# IMAGE_WAVEPIX 
# This functions generates an image (2D array) of the wavelength distribution
def image_wavepix(coeffs, size):
    """
    Parameters
    ----------
    coeffs : an array with the coefficients required to convert wavelength to 
    pixel. (Load from calibration file)
    size : an array with height and width of the SLM.

    Returns
    -------
    image_wavepix_array : 2D array of the wavelength distribution

    """
    x = np.arange(1, size[1], 1)
    image_wavepix_array = npm.repmat(np.polyval(coeffs, x), size[0], 1)
    return image_wavepix_array

# DEFORMATION CORRECTION
def deformation_correction(path, coeff_wavepix, beam_pos):
    """
    Parameters
    ----------
    path : The path to the deform coeff matrix, an interpolating polynomial 
    relating pixelwise the phase deformation to the wavelength (in nm).
    
    coeff_wavepix : a matrix containing the vectors containing polynomials 
    required to convert pixel to wavelength. 
    
    beam_pos : a vector containing the boundaries between each beams.
    
    Returns
    -------
    deform : deformation phase image, deform, which should be added 
    (from what I understand from the User manual)to the desired phase image

    """
    Coeff_1 = import_deform_coeff(path+"coeff_deform_slm_2021_1.txt")
    Coeff_2 = import_deform_coeff(path+"coeff_deform_slm_2021_2.txt")
    Coeff_3 = import_deform_coeff(path+"coeff_deform_slm_2021_3.txt")
    Coeff_4 = import_deform_coeff(path+"coeff_deform_slm_2021_4.txt")
    
    deform = np.zeros((len(Coeff_1), len(np.transpose(Coeff_1))))
    
    I = range(1,len(np.transpose(Coeff_1))+1)
    for k in range(1, len(coeff_wavepix[0])+1):
        for i in range(1,len(np.transpose(Coeff_1))+1):
            if k == 1:
                Wavelength = np.polyval(coeff_wavepix[0], I)
                for j in range(1, len(beam_pos)+1):
                    squeeze = np.array([Coeff_1[j-1,i-1],Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]])
                    deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1])
        
            elif k == len(coeff_wavepix[0]):
                Wavelength = np.polyval(coeff_wavepix[k-1], I)
                for j in beam_pos[k-2]+np.array(range(1, len(Coeff_1))):
                   squeeze = np.array([Coeff_1[j-1,i-1],Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]]) 
                   deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1]) 
            else: 
               Wavelength = np.polyval(coeff_wavepix[k-1], I)
               for j in beam_pos[k-2]+np.array(range(1, beam_pos[k-1])):
                    squeeze = np.array([Coeff_1[j-1,i-1],Coeff_2[j-1,i-1], Coeff_3[j-1,i-1], Coeff_4[j-1,i-1]]) 
                    deform[j-1,i-1] = (2*np.pi/255)*f_polyval(squeeze, Wavelength[i-1])
                    
    deform = np.unwrap(deform, axis=1)
    return deform

# Phase_2gs_image
def phase_2gs_image(path, size, coeff_wavepix, beam_pos):
    """
    Parameters
    ----------
    path : the path to the calibration files.
    
    size :  an array with height and width of the SLM.
    
    coeff_wavepix : a matrix containing the vectors containing polynomials 
    required to convert pixel to wavelength. 
    
    beam_pos : a vector containing the boundaries between each beams.

    Returns
    -------
    image_gs : Generates grey scale image.

    """
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
            image_gs = np.append(image_gs, npm.repmat(func(wave), size[0]-(beam_pos[k-2]),1))
            
        else:
            wave = np.polyval(coeff_wavepix[k-1], np.arange(1, size[1]+1))
            wave[np.where(wave>700)] = 700*np.ones(len(np.where(wave>700)))
            image_gs = np.append(image_gs, npm.repmat(func(wave), beam_pos[k-1]-beam_pos[k-2],1))

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
# Testing place
##############################################################################
# size = [10, 150]
# coeff_wavepix = [[2, 3], [5, 7], [7,8]]
# beam_pos = [1, 10]

# path = "C:/Users/esteb/Desktop/Traducing_files/SLM phase to greyscale/"
# phase_2gs_image(path, size, coeff_wavepix)