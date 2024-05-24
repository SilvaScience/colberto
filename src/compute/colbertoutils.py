#### This modules hosts all general purpose functions for Colbert
from scipy.constants import c,h,pi,e
def waveToeV(wave):
    """
    Converts vacuum wavelengths (m) to energy in eV
    """ 
    return h*c/wave/e

def waveToFreq(wave):
    """
    Converts vacuum wavelengths (m) to frequency in Hz
    """ 
    return c/wave

def waveToAngFreq(wave):
    """
    Converts vacuum wavelengths (m) to angular frequency in rad.Hz
    """ 
    return 2*pi*c/wave

def angFreqToWave(angFreq):
    """
    Converts angular frequency in rad.Hz to vacuum wavelengths (m)
    """ 
    return 2*pi*c/angFreq

def angFreqToFreq(angFreq):
    """
    Converts angular frequency in rad.Hz to frequency (Hz)
    """ 
    return waveToFreq(angFreqToWave(angFreq))

def angFreqToeV(angFreq):
    """
    Converts angular frequency in rad.Hz to frequency (Hz)
    """ 
    return waveToeV(angFreqToWave(angFreq))