"""
Calibration classes for different types of calibration. Each calibration creates a new thread that runs until the
calibration has finished or was requested to stop. Calibrations can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each calibration, parameter are read from Main script and remain
until the measurement has finished.
"""
import time
from PyQt5 import QtCore
import numpy as np
from numpy.polynomial.polynomial import Polynomial
from numpy.polynomial import Polynomial as P
from pathlib import Path
from scipy import special
from compute import colbertoutils as co
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
import logging
import os
import math
import datetime
from scipy.ndimage import uniform_filter
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)

class VerticalBeamCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will gradually turn on rows of the SLM and record the intensity on the spectrometer.
        signals:
            - sendSpectrum : wavelength and intensity detected by the spectrometer
            - send_intensities: Row index and detected spectrally integrated intensity
            - send_vertical_calibration_data: tuple, first is label 'vertical_calibration_data' and second is row and intensities tuple
            - sendProgress :  float representing the progress of the measurement.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_intensities = QtCore.pyqtSignal(np.ndarray,np.ndarray)
    send_vertical_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, devices, grating_period,rows_multiple,demo=False):
        '''
         Initializes the Vertical beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - grating_period (int): the grating period in pixels
             - rows_multiple (int): Multiples by which to increment the length of the vertical grating
             - demo (bool): Run the calibration in demo mode (True) or not (False, default) 
        ''' 
        super(VerticalBeamCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        self.rows=np.arange(0,self.SLM.get_height(),rows_multiple)
        self.intensities= np.zeros(self.rows.shape)# preallocate spec array
        self.vertical_calibration_data={
            'rows' : self.rows,
            'intensities' : self.intensities
        }
        # Configure single beam over which the rows will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_gratingPeriod(grating_period)
        self.isDemo= demo
        if self.isDemo:
            fakeBeamshape = lambda x,x0: 1000*(special.erf((x-x0)/10)+1)
            self.demoIntensities=fakeBeamshape(self.rows,self.SLM.get_height()/8)+fakeBeamshape(self.rows,3*self.SLM.get_height()/8)+fakeBeamshape(self.rows,5*self.SLM.get_height()/8)+fakeBeamshape(self.rows,7*self.SLM.get_height()/8)

    def run(self):
        logger.info('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' started')
        for i,row in enumerate(self.rows):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_beamVerticalDelimiters([0, row])
                image_output=self.monobeam.makeGrating()                
                self.SLM.write_image(image_output)
                self.take_spectrum(i)
                self.intensities[i]=np.sum(self.spec) if not self.isDemo else self.demoIntensities[i] 
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.vertical_calibration_data['rows']=self.rows
                if i>=1:
                    self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.vertical_calibration_data['rows']=self.rows
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        logger.info('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self,i):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo and i>=1:
            self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        logger.info(time.strftime('%H:%M:%S') + ' Request Stop')


class SpectralBeamCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will scan the columns of the SLM with a grating stripe and record the intensity on the spectrometer.
        signals:
            - sendSpectrum : wavelength and intensity detected by the spectrometer
            - send_intensities: tuple with column index (np.1darray), wavelength axis (np.1darray) and associated spectra (np.2darray)
            - send_spectral_calibration_data: tuple, first is label 'vertical_calibration_data' and second is row and intensities tuple
            - sendProgress :  float representing the progress of the measurement.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_intensities= QtCore.pyqtSignal(np.ndarray,np.ndarray,np.ndarray)
    send_spectral_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices,grating_period,column_increment, column_width,demo=False):
        '''
         Initializes the Spectral beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - grating_period: (int) the vertical period (in pixels) of the phase grating
             - column_increment: (int) the step by which to shift the columns 
             - column_width: (int) the width (in pixels) of the scanned column
             - demo (bool): Run the calibration in demo mode (True) or not (False, default) 
        ''' 
        super(SpectralBeamCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        self.columns=np.arange(0,self.SLM.get_width(),column_increment,dtype=int)
        self.columns_out=[]
        self.column_width=column_width
        #self.intensities= np.zeros((len(self.columns),len(self.wls)))# preallocate spec array
        self.intensities=[]
        self.spectral_calibration_data={
            'columns' : self.columns,
            'wavelengths' : self.wls,
            'intensities' : self.intensities
        }
        # Configure single beam over which the columns will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_gratingPeriod(grating_period)
        self.isDemo= demo

    def run(self):
        for i,column in enumerate(self.columns):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_beamHorizontalDelimiters([column-self.column_width//2,column+self.column_width//2])
                image_output=self.monobeam.makeGrating()                
                self.SLM.write_image(image_output)
                self.take_spectrum(i)
                if self.isDemo:
                    fakeSpectrum=self.fakeSignal(self.wls,column,self.column_width)
                    self.intensities.append(fakeSpectrum)
                    self.sendSpectrum.emit(self.wls,fakeSpectrum)
                else:
                    self.intensities.append(self.spec)
                self.columns_out.append(column)
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.columns)*100)
                self.spectral_calibration_data={
                    'columns' : np.array(self.columns_out),
                    'wavelengths' : self.wls,
                    'data' : np.array(self.intensities)
                }
                if i>=1:
                    self.send_intensities.emit(np.array(self.columns_out),self.wls,np.array(self.intensities))
        self.send_spectral_calibration_data.emit(('spectral_calibration_raw_data',self.spectral_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        logger.info('Spectral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self,i):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo and i>=1:
            self.sendSpectrum.emit(self.wls, self.spec)
    def stop(self):
        self.terminate = True
        logger.info(time.strftime('%H:%M:%S') + ' Request Stop')
    def fakeSignal(self,wls,current_col,col_width):
        wave_per_pix=0.1 #Arbitrary but reasonnable parameters to simulate data acq.
        min_wave=600
        fakeSpectrum=np.zeros(wls.shape)
        for i,wave in enumerate(wls):
            if wave-min_wave<=(current_col+col_width/2)*wave_per_pix and wave-min_wave>(current_col-col_width/2)*wave_per_pix:
                fakeSpectrum[i]= 1000
        fakeSpectrum=fakeSpectrum+10*np.random.rand(len(fakeSpectrum))
        return fakeSpectrum

    
class FitSpectralBeamCalibration(QtCore.QThread):
    '''
        Manipulates the data to extract the SLM pixel to wavelength calibration from a previous measurement:
            - send_maxima : column and wavelength of maximum detected by the spectrometer
            - send_polynomial: np.ndarray representing a polynomial p[0]+p[1]*x+p[2]*x**2+...
    '''
    send_maxima = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_polynomial= QtCore.pyqtSignal(Polynomial)
    send_spectral_calibration_data = QtCore.pyqtSignal(tuple)
    send_spectral_calibration_fit = QtCore.pyqtSignal(tuple)

    def __init__(self,boundaries,increment,spectral_calibration_data=None):
        '''
         Initializes the spectral beam calibration fitting
         input:
             - boundaries: (np.ndarray) Shortest and longest wavelengths to consider when manipulating the spectra calibration data.
        ''' 
        self.boundaries = boundaries
        self.increment = increment
        super(FitSpectralBeamCalibration, self).__init__()

    def extractMaxima(self, column_array, wavelength_array, data):
        '''
            Finds the maximum of spectra
            input:
                - column_array: (np.ndarray) 1D array holding the scanned axis of the 2D data plot
                - wavelength_array: (np.ndarray) 1D array holding the wavelength axis of the 2D data plot
                - data: (np.ndarray) 2D array of scanned spectra where spectra are arranged by row
                - boundaries: (np.1darray) Minimum and maximal wavelengths to consider in the fitting
            output:
                - column_out: (np.ndarray) indices of the SLM columns. Emitted through send_maxima signal
                - wavelengths_out: (np.ndarray) maxima of the spectra acquired in spectral calibration measurement. Emitted through send_maxima signal
        '''
        wavelengths = []
        boundaries = self.boundaries
        self.column_array = column_array
        self.wavelength_array = wavelength_array
        self.data = data

        spec_bounds = getattr(self, "spec_wl_bounds", None)

        wave_min_idx = int(np.argmin(np.abs(spec_bounds[0] - self.wavelength_array)))
        wave_max_idx = int(np.argmin(np.abs(spec_bounds[1] - self.wavelength_array)))

        self.wavelength_array = self.wavelength_array[wave_min_idx:wave_max_idx + 1]

        for spectrum in data:
            spectrum_window = spectrum[wave_min_idx:wave_max_idx]
            wavelengths.append(self.wavelength_array[np.mean(np.argmax(spectrum_window), dtype=int)])
        wavelengths = np.array(wavelengths)
        index = np.arange(len(wavelengths)) * self.increment
        columns_out = column_array[np.logical_and(index >= boundaries[0], index <= boundaries[1])]
        wavelengths_out = wavelengths[np.logical_and(index >= boundaries[0], index <= boundaries[1])]
        self.send_maxima.emit(columns_out, wavelengths_out * 1e-9)
        self.spectral_calibration_processed_data = {
            'columns': columns_out,
            'wavelengths': wavelengths_out
        }
        self.send_spectral_calibration_data.emit(('spectral_calibration_processed_data', self.spectral_calibration_processed_data))
        return columns_out, wavelengths_out

    def set_boundaries(self,boundaries):
        '''
            Method to change the spectral beam fitting algorithm wavelength boundaries and update the results
            input:
                - boundaries: (np.ndarray) Shortest and longest wavelengths to consider when manipulating the spectra calibration data.
        '''
        self.boundaries=boundaries
        self.extractMaxima(self.column_array,self.wavelength_array,self.data)

    def fitSpectraMaxima(self,columns,maxima_wavelengths,degree):
        '''
            Extracts the polynomial converting SLM column into the incident wavelength
            input:
                - columns: (nd.array) array of SLM columns indices
                - maxima_wavelenghts: (nd.array) array of the maxima (wavelengths) of the spectral calibration measurements
        '''
        self.fit_polynomial=Polynomial.fit(columns,maxima_wavelengths*1e-9,deg=degree)
        self.send_polynomial.emit(self.fit_polynomial)
        self.send_spectral_calibration_fit.emit(('spectral_calibration_fit',self.fit_polynomial))
        
class AcquireBackground(QtCore.QThread):
    """
        Class implementing the background acquisition for chirp scans.
        Signals are:
        - sendSpectrum : wavelength and intensity detected by the spectrometer
        - sendProgress: float representing the progress of the measurement.
    """
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    send_background = QtCore.pyqtSignal(tuple)

    def __init__(self, devices):
        
        super(AcquireBackground, self).__init__()
        self.terminate = False
        self.acquire_measurement = True
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.background = []

    def run(self):
        image_output = np.zeros((self.SLM.get_height(),self.SLM.get_width()))              
        self.SLM.write_image(image_output)

        self.wls = self.spectrometer.get_wavelength()
        self.background = np.array(self.spectrometer.get_intensities())
        self.sendProgress.emit(50)
        self.background = np.array(self.spectrometer.get_intensities())
        self.background_data = {
                                'spec' : self.background,
                                'wavelengths' : self.wls,
                                }
        self.send_background.emit(('background_data', self.background_data))
        self.sendSpectrum.emit(self.wls, self.background)
        logger.info(time.strftime('%H:%M:%S') + ' Finished')
        self.sendProgress.emit(100)
        self.stop()

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

class ChirpCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will scan the columns of the SLM with a grating stripe and record the intensity on the spectrometer.
        signals:
            - sendSpectrum: wavelength and intensity detected by the spectrometer
            - send_chirp: 
            - send_chirp_calibration_data: 
            - sendProgress: float representing the progress of the measurement.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_chirp = QtCore.pyqtSignal(np.ndarray,np.ndarray,np.ndarray)
    send_chirp_calibration_data = QtCore.pyqtSignal(tuple)
    send_beam = QtCore.pyqtSignal(object)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, background, grating_period, compression_carrier_wavelength, chirp_step, chirp_max, chirp_min, beam_name, beam, spectral_calibration=None, demo=False):
        '''
         Initializes the semporal beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - background: the background to be remove of each measurements
             - grating_period: (int) the vertical period (in pixels) of the phase grating
             - compression_carrier_wavlength: set in the GUI in nm
             - chirp_step: set in the GUI in fs^2
             - chrip_max: set in the GUI in fs^2
             - chirp_min: set in the GUI in fs^2
             - beam_name: set in the GUI 
             - beam: disctionnary of all beam attributes
             - spectral_calibration: pixel to wavelength calibration obtained (polynomial)
             - demo: is demo or not
        ''' 
        super(ChirpCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        
        self.wls = self.spectrometer.get_wavelength()
        self.background = background
        self.spectra = []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.chirp=np.arange(chirp_min,chirp_max,chirp_step,dtype=int) 
        self.intensities=[]
        self.spectral_calibration_data={
            'Chirp' : self.chirp,
            'wavelengths' : self.wls,
            'intensities' : self.intensities
        }

        self.isDemo= demo
        self.beam_name = beam_name
        self.beam = beam
        if spectral_calibration == None:
            self.beam.set_pixelToWavelength(Polynomial(1e-9*np.array([compression_carrier_wavelength-100,1/10]))) # arbitrary polynomial spectral calibration
            logger.warning('%s Arbitrary spectral calibration used'%datetime.datetime.now())
        self.beam.set_compressionCarrierWave(compression_carrier_wavelength*1e-9) 
        self.beam.set_gratingPeriod(grating_period)
        self.carrierWls = compression_carrier_wavelength
    
    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
                if self.isDemo:
                    project_folder = Path(__file__).parent.parent.resolve()
                    file_path = os.path.join(project_folder, "Chirp_dataset.txt")
                    a = np.loadtxt(file_path)

                    self.wls = a[-1]
                    self.Chirp_data= a[-2]
                    f = len(self.Chirp_data)  # default to full length
                    for h in range(len(self.Chirp_data)):
                        if self.Chirp_data[h] == 0:
                            f = h
                            break

                    self.Chirp_data = self.Chirp_data[:f]   
                    self.data = a[:-3]
                    # Emit the data through signals

                    for i in range(len(self.Chirp_data)):
                        if not self.terminate:
                            self.Chirp_calibration_data={
                                'Chirp' : np.array(self.Chirp_data),
                                'wavelengths' : np.array(self.wls),
                                'data' : np.array(self.data)
                                }
    
                            self.sendProgress.emit(i/len(self.Chirp_data)*100)
                            self.send_chirp.emit(np.array(self.Chirp_data[:i]), np.array(self.wls), np.array(self.data[:i]))
                else:
                    for i in range(len(self.chirp)):
                        if not self.terminate:
                            self.coeffs = np.array([0, 0, self.chirp[i]])
                            self.beam.set_currentPhase(P(self.coeffs), mode='relative', unit='fs')
                            self.send_beam.emit((self.beam_name, self.beam))
                            image_output = self.beam.makeGrating()                
                            self.SLM.write_image(image_output)
                            self.take_spectrum(i)
                            self.intensities.append(self.spec)
                            self.sendProgress.emit(i/len(self.chirp)*100)
                            self.Chirp_calibration_data={
                                'Chirp' : self.chirp,
                                'wavelengths' : self.wls,
                                'data' : np.array(self.intensities)
                                }
                            if i>=3:
                                # indexes = np.where(
                                #     (self.wls >= (self.carrierWls/2 - 100)) &
                                #     (self.wls <= (self.carrierWls/2 + 100))
                                # )[0]
                                # self.send_chirp.emit(self.chirp[3:i],self.wls[indexes],np.array(self.intensities)[3:i,indexes])
                                self.send_chirp.emit(self.chirp[3:i],self.wls,np.array(self.intensities)[3:i,:])
        self.send_chirp_calibration_data.emit(('chirp_calibration_raw_data',self.Chirp_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Temporal Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')
        #np.savetxt('chirp.txt', self.chirp)
        #np.savetxt('wls.txt', self.wls)
        #np.savetxt('intensities.txt', np.array(self.intensities))
    def stop(self):
            self.terminate = True
            print(time.strftime('%H:%M:%S') + ' Request Stop')
    def take_spectrum(self,i):
        if i == 0: 
            self.spec = np.array(self.spectrometer.get_intensities())
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo and i>=1:
            self.spec = self.spec-self.background
            self.sendSpectrum.emit(self.wls, self.spec)

class FitTemporalBeamCalibration(QtCore.QThread):
    '''
        Manipulates the data to extract the chirp calibration from a previous measurement:
            - send_maxima : column and wavelength of maximum detected by the spectrometer
            - send_polynomial: np.ndarray representing a polynomial p[0]+p[1]*x+p[2]*x**2+...
    '''
    send_chirp_region = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    send_chirp_fit = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_polynomial= QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_chirp_calibration_data = QtCore.pyqtSignal(tuple)
    send_chirp_calibration_fit = QtCore.pyqtSignal(tuple)

    def __init__(self, boundaries, temporal_calibration_data=None):
        '''
         Initializes the spectral beam calibration fitting
         input:
             - boundaries: (np.ndarray) Shortest and longest wavelengths to consider when manipulating the spectra calibration data.
        ''' 
        self.boundaries = boundaries

        super(FitTemporalBeamCalibration, self).__init__()

    def set_SNR(self, chirpdata, SNR_threshold):
        '''
            Method to remove data below a given SNR:
                - SNR: (int) Minimal signal to noise ratio.
        '''
        self.SNR = SNR_threshold
        boundaries = self.boundaries
        self.chirp_array = chirpdata['Chirp']
        self.wavelength_array = chirpdata['wavelengths']
        self.data = chirpdata['data']

        # --- Compute local statistics to characterize the data structure ---

        # Compute a smoothed version of the data using a uniform (mean) filter.
        # This acts like a moving average over a square region of size `window × window`.
        # It represents the local average intensity (the "baseline") at each point.
        local_mean = uniform_filter(self.data, size=10)

        # Compute the local average of the squared data (⟨x²⟩) over the same window.
        # This is used to estimate the variance in each neighborhood.
        local_sq_mean = uniform_filter(self.data**2, size=10)

        # Compute the local standard deviation using σ = sqrt(⟨x²⟩ - ⟨x⟩²).
        # This quantifies local fluctuations (i.e. how noisy or structured the region is).
        # Avoid small negative values due to rounding
        variance = local_sq_mean - local_mean**2
        variance = np.clip(variance, 0, None)
        local_std = np.sqrt(variance)

        # --- Identify regions likely to be pure noise ---

        # Define a "score" that combines:
        #   - the absolute local mean (to find near-zero regions)
        #   - the local standard deviation (to find low-variance regions)
        # Regions with both low mean and low variance are good candidates for noise-only areas.
        score = np.abs(local_mean) + local_std

        # Compute a threshold value corresponding to the bottom `frac` percentile of the score distribution.
        # For example, if frac=0.1, we keep the 10% of points with the smallest (mean + std) scores.
        threshold = np.percentile(score, 100 * 0.1)

        # Create a boolean mask identifying the pixels (or points) that fall below that threshold.
        # True → region is considered noise-only
        # False → region might contain signal
        mask = score <= threshold

        # --- Compute noise level safely ---
        finite_mask = np.isfinite(self.data)
        combined_mask = mask & finite_mask

        if np.any(combined_mask) and np.sum(combined_mask) > 1:
            noise_level = np.std(self.data[combined_mask])
        else:
            noise_level = np.std(self.data[finite_mask])

        # --- Filter based on SNR ---
        SNR = np.abs(self.data) / noise_level
        data_filtered = np.where(SNR >= SNR_threshold, self.data, 0)

        chirp_array_region = self.chirp_array[1:-1]
        mask = np.logical_and(self.wavelength_array >= boundaries[0], self.wavelength_array <= boundaries[1])
        wavelength_array_region = self.wavelength_array[mask]
        data_filtered_region = data_filtered[1:-1, mask]

        self.send_chirp_region.emit(chirp_array_region, wavelength_array_region, data_filtered_region)
        self.temporal_calibration_processed_data={
            'chirps': chirp_array_region,
            'wavelengths': wavelength_array_region,
            'data': data_filtered_region
        }
        self.send_chirp_calibration_data.emit(('temporal_calibration_processed_data', self.temporal_calibration_processed_data))

    def set_boundaries(self, chirpdata, boundaries, SNR_threshold):
        '''
            Method to change the temporal beam fitting algorithm wavelength boundaries and update the results
            input:
                - boundaries: (np.ndarray) Shortest and longest wavelengths to consider when manipulating the spectra calibration data.
        '''
        self.boundaries = boundaries
        self.SNR_threshold = SNR_threshold
        self.set_SNR(chirpdata, self.SNR_threshold)

    def fit_chirp_scan(self, wavelength_array, chirp_array, data, deg, carrier_wavelength):
        '''
            Fit the polynomial 
                - columns: (nd.array) array of SLM columns indices
                - maxima_wavelenghts: (nd.array) array of the maxima (wavelengths) of the spectral calibration measurements
        '''
        self.chirp_array = chirp_array
        self.wavelength_array = wavelength_array
        self.data = data
        
        # Loop through each wavelength 
        max_chirp_values = []
        wavelength_values = []
        for wls in range(self.data.shape[1]):
            intensity_column = self.data[:, wls]
            max_row_index = np.argmax(intensity_column)
            if max_row_index == 0:
                continue
            max_chirp_values.append(self.chirp_array[max_row_index])
            wavelength_values.append(self.wavelength_array[wls])
        max_chirp_values = np.array(max_chirp_values)
        wavelength_values = np.array(wavelength_values)
        omega_values = 0.5*co.waveToAngFreq(np.array(wavelength_values) * 1e-9) # rad Hz

        # Shifted frequency around the carrier
        omega_carrier = co.waveToAngFreq(carrier_wavelength * 1e-9) # rad Hz
        omega_shifted = omega_values-omega_carrier

        # Fit a nth order polynimial
        #self.fit_polynomial = Polynomial.fit(omega_shifted, max_chirp_values, deg)
        coeffs = np.polyfit(omega_shifted, max_chirp_values, deg)
        self.fit_polynomial = np.polyval(coeffs, omega_shifted)
        self.send_chirp_fit.emit(omega_shifted, max_chirp_values)
        self.send_polynomial.emit(omega_shifted, self.fit_polynomial)
        self.send_chirp_calibration_fit.emit(('temporal_calibration_processed_fit', self.fit_polynomial))

        # Get the coefficients
        self.coeffs = coeffs[::-1]
        return self.coeffs
    
class DelayCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will scan the delay between two beams
            - sendProgress: float representing the progress of the measurement.
            - sendSpectrum: wavelength and intensity detected by the spectrometer.
            - sendBeam: signal to the beam explorer
            - sendCrossCorrelation: wavelength, delay and intensity for the Delay_scan_plot
            - sendCrossCorrelationData: wavelength, delay and intensity for DataHandling calibration
            - sendCrossCorrelationRegion: delay and intensity (wavelength integrated) for the Delay_fit_plot
            - sendCrossCorrelationFit: fit of the Delay_fit_plot
            - sendCrossCorrelationFitData: delay and intensity for DataHandling calibration
            - sendCrossCorrelationDelay: fitted delay for DataHandling calibration
    '''
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeam = QtCore.pyqtSignal(object)
    sendCrossCorrelation = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    sendCrossCorrelationData = QtCore.pyqtSignal(tuple)
    sendCrossCorrelationRegion = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendCrossCorrelationRegionData = QtCore.pyqtSignal(tuple)
    sendCrossCorrelationRegionFit = QtCore.pyqtSignal(np.ndarray, np.ndarray, float, float)
    sendCrossCorrelationRegionFitData = QtCore.pyqtSignal(tuple)

    def __init__(self, devices, background, grating_period, delay_carrier_wavelength, delay_step, delay_max, delay_min, refBeamName, secBeamName, refBeam, secBeam, spectral_calibration=None, demo=False):
        '''
            Initializes the semporal beam calibration measurement
            input:
                - devices: the devices dictionnary holding at least a spectrometer and a SLM
                - background: the background to be remove of each measurements
                - grating_period: (int) the vertical period (in pixels) of the phase grating
                - delay_carrier_wavlength: set in the GUI in nm
                - delay_step: set in the GUI in fs^2
                - delay_max: set in the GUI in fs^2
                - delay_min: set in the GUI in fs^2
                - refBeamName: set in the GUI
                - secBeamName: set in the GUI
                - refBeam: dictionnary of reference beam attributes
                - secBeam: dictionnary of second beam attributes
                - spectral_calibration: pixel to wavelength calibration obtained (polynomial)
                - demo: is demo or not
        ''' 
        super(DelayCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM = devices['SLM']
        
        self.wls = self.spectrometer.get_wavelength()
        self.background = background
        self.spectra = []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.delay = np.arange(delay_min, delay_max, delay_step, dtype=int) 
        self.intensities = []
        self.delay_calibration_data={
            'delay' : self.delay,
            'wavelengths' : self.wls,
            'intensities' : self.intensities
        }
        self.isDemo = demo
        
        # Reference beam
        self.refBeamName = refBeamName
        self.refBeam = refBeam
        self.refBeam.set_delayCarrierWave(delay_carrier_wavelength*1e-9) 
        self.refBeam.set_gratingPeriod(grating_period)
        self.refBeam.set_currentPhase(P(self.refBeam.get_optimalPhase(units_to_return='fs').coef), mode='absolute', unit='fs')
        self.sendBeam.emit((self.refBeamName, self.refBeam))
        self.ref_image = self.refBeam.makeGrating()

        # Second beam 
        self.secBeamName = secBeamName
        self.secBeam = secBeam
        self.secBeam.set_delayCarrierWave(delay_carrier_wavelength*1e-9)
        self.secBeam.set_gratingPeriod(grating_period)

        if spectral_calibration == None:
            self.refBeam.set_pixelToWavelength(Polynomial(1e-9*np.array([delay_carrier_wavelength-100,1/10]))) # arbitrary polynomial spectral calibration
            self.secBeam.set_pixelToWavelength(Polynomial(1e-9*np.array([delay_carrier_wavelength-100,1/10]))) # arbitrary polynomial spectral calibration
            logger.warning('%s Arbitrary spectral calibration used'%datetime.datetime.now())

    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
                if self.isDemo:
                    return
                else:
                    for i in range(len(self.delay)):
                        if not self.terminate:
                            self.coeffs = np.array([0, self.delay[i]])
                            self.secBeam.set_currentPhase(P(self.coeffs), mode='relative', unit='fs')
                            self.sendBeam.emit((self.secBeamName, self.secBeam))
                            self.sec_image = self.secBeam.makeGrating()
                            image_output = self.ref_image+self.sec_image

                            self.SLM.write_image(image_output)
                            self.take_spectrum(i)
                            self.intensities.append(self.spec)
                            self.sendProgress.emit(i/len(self.delay)*100)
                            self.delay_calibration_data={
                                'delay' : self.delay,
                                'wavelengths' : self.wls,
                                'data' : np.array(self.intensities)
                                }
                            if i>=3:
                                self.sendCrossCorrelation.emit(self.delay[3:i], self.wls, np.array(self.intensities)[3:i, :])
        self.sendCrossCorrelationData.emit((f"Delay_calibration_raw_data_{self.refBeamName}_{self.secBeamName}", self.delay_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Delay Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')
    
    def stop(self):
            self.terminate = True
            print(time.strftime('%H:%M:%S') + ' Request Stop')
    
    def take_spectrum(self, i):
        if i == 0: 
            self.shg = np.array(self.spectrometer.get_intensities())
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo and i>=1:
            self.spec = self.spec-self.background-self.shg
            self.sendSpectrum.emit(self.wls, self.spec)

    def set_SNR(self, delaydata, SNR_threshold, boundaries):
        '''
            Method to remove data below a given SNR:
                - SNR: (int) Minimal signal to noise ratio.
        '''
        self.SNR = SNR_threshold
        self.boundaries = boundaries
        self.delay_array = delaydata['delay']
        self.wavelength_array = delaydata['wavelengths']
        self.data = delaydata['data']

        # --- Compute local statistics to characterize the data structure ---

        # Compute a smoothed version of the data using a uniform (mean) filter.
        # This acts like a moving average over a square region of size `window × window`.
        # It represents the local average intensity (the "baseline") at each point.
        local_mean = uniform_filter(self.data, size=10)

        # Compute the local average of the squared data (⟨x²⟩) over the same window.
        # This is used to estimate the variance in each neighborhood.
        local_sq_mean = uniform_filter(self.data**2, size=10)

        # Compute the local standard deviation using σ = sqrt(⟨x²⟩ - ⟨x⟩²).
        # This quantifies local fluctuations (i.e. how noisy or structured the region is).
        # Avoid small negative values due to rounding
        variance = local_sq_mean - local_mean**2
        variance = np.clip(variance, 0, None)
        local_std = np.sqrt(variance)

        # --- Identify regions likely to be pure noise ---

        # Define a "score" that combines:
        #   - the absolute local mean (to find near-zero regions)
        #   - the local standard deviation (to find low-variance regions)
        # Regions with both low mean and low variance are good candidates for noise-only areas.
        score = np.abs(local_mean) + local_std

        # Compute a threshold value corresponding to the bottom `frac` percentile of the score distribution.
        # For example, if frac=0.1, we keep the 10% of points with the smallest (mean + std) scores.
        threshold = np.percentile(score, 100 * 0.1)

        # Create a boolean mask identifying the pixels (or points) that fall below that threshold.
        # True → region is considered noise-only
        # False → region might contain signal
        mask = score <= threshold

        # --- Compute noise level safely ---
        finite_mask = np.isfinite(self.data)
        combined_mask = mask & finite_mask

        if np.any(combined_mask) and np.sum(combined_mask) > 1:
            noise_level = np.std(self.data[combined_mask])
        else:
            noise_level = np.std(self.data[finite_mask])

        # --- Filter based on SNR ---
        SNR = np.abs(self.data) / noise_level
        data_filtered = np.where(SNR >= SNR_threshold, self.data, 0)

        delay_array_region = self.delay_array[1:-1]
        mask = np.logical_and(self.wavelength_array >= boundaries[0], self.wavelength_array <= boundaries[1])
        wavelength_array_region = self.wavelength_array[mask]
        data_filtered_region = data_filtered[1:-1, mask]
        data_integrated = np.sum(data_filtered_region, axis=1)
        data_integrated_normalized = data_integrated/np.max(data_integrated)
        data_integrated_normalized = -(data_integrated_normalized-np.max(data_integrated_normalized))

        self.sendCrossCorrelationRegion.emit(delay_array_region, data_integrated_normalized)
        self.delay_calibration_processed_data={
            'delay': delay_array_region,
            'wavelength': wavelength_array_region,
            'data': data_integrated_normalized
        }
        self.sendCrossCorrelationRegionData.emit(('delay_calibration_processed_data', self.delay_calibration_processed_data))

    def get_fit(self, delay_data, normalized_intensity_data):
        '''
            Compute a gaussian fit on the processed delay calibration data
                - delay_data: vector of the delays [fs]
                - normalized_intensity_data: vector of data normalized
        '''
        self.delay = delay_data
        self.intensity = normalized_intensity_data

        A0 = np.max(self.intensity) - np.min(self.intensity)
        mu0 = self.delay[np.argmax(self.intensity)]
        sigma0 = (self.delay[-1] - self.delay[0]) / 10   # rough width guess
        C0 = np.min(self.intensity)

        p0 = [A0, mu0, sigma0, C0]
        bounds = ([-np.inf, self.delay.min(), 0, -np.inf], [ np.inf, self.delay.max(), np.inf, np.inf])
        popt, pcov = curve_fit(lambda x, A, mu, sigma, C: A * np.exp(-(x - mu)**2 / (2 * sigma**2)) + C, self.delay, self.intensity, p0=p0, bounds=bounds)
        A, mu, sigma, C = popt
        self.fitted_intensity = (A * np.exp(-(self.delay - mu)**2 / (2 * sigma**2)) + C)
        self.sendCrossCorrelationRegionFit.emit(self.delay, self.fitted_intensity, mu, sigma)

        self.gaussian_fit_params = {
            "A": A,
            "mu": mu,
            "sigma": sigma,
            "C": C,
            "covariance": pcov,
            "delay": self.delay,
            "intensity": self.fitted_intensity
        }
        self.sendCrossCorrelationRegionFitData.emit(('delay_calibration_processed_data_fit', self.gaussian_fit_params))
