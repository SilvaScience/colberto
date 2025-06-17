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
from pathlib import Path
from scipy import special
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
import logging

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
    send_intensities= QtCore.pyqtSignal(np.ndarray,np.ndarray)
    send_vertical_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, grating_period,rows_multiple,demo=False):
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
                self.take_spectrum()
                self.intensities[i]=np.sum(self.spec) if not self.isDemo else self.demoIntensities[i] 
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.vertical_calibration_data['rows']=self.rows
                self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.vertical_calibration_data['rows']=self.rows
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        logger.info('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
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
                self.take_spectrum()
                if self.isDemo:
                    fakeSpectrum=self.fakeSignal(self.wls,column,self.column_width)
                    self.intensities.append(fakeSpectrum)
                    self.sendSpectrum.emit(self.wls,fakeSpectrum)
                else:
                    self.intensities.append(self.spectra)
                self.columns_out.append(column)
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.columns)*100)
                self.spectral_calibration_data={
                    'columns' : np.array(self.columns_out),
                    'wavelengths' : self.wls,
                    'data' : np.array(self.intensities)
                }
                self.send_intensities.emit(np.array(self.columns_out),self.wls,np.array(self.intensities))
        self.send_spectral_calibration_data.emit(('spectral_calibration_raw_data',self.spectral_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        logger.info('Spêctral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo:
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

    def __init__(self,boundaries,spectral_calibration_data=None):
        '''
         Initializes the spectral beam calibration fitting
         input:
             - boundaries: (np.ndarray) Shortest and longest wavelengths to consider when manipulating the spectra calibration data.
        ''' 
        self.boundaries=boundaries
        super(FitSpectralBeamCalibration, self).__init__()

    def extractMaxima(self,column_array,wavelength_array, data):
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
        wavelengths=[]
        boundaries=self.boundaries
        self.column_array=column_array
        self.wavelength_array=wavelength_array
        self.data=data
        for spectrum in data:
            wavelengths.append(wavelength_array[np.mean(np.argmax(spectrum),dtype=int)])
        wavelengths=np.array(wavelengths)
        columns_out=column_array[np.logical_and(wavelengths>=boundaries[0],wavelengths<=boundaries[1])]
        wavelengths_out=wavelengths[np.logical_and(wavelengths>=boundaries[0],wavelengths<=boundaries[1])]
        self.send_maxima.emit(columns_out,wavelengths_out)
        self.spectral_calibration_processed_data={
            'columns':columns_out,
            'wavelengths':wavelengths_out
        }
        self.send_spectral_calibration_data.emit(('spectral_calibration_processed_data',self.spectral_calibration_processed_data))
        return columns_out,wavelengths_out

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
        self.fit_polynomial=Polynomial.fit(columns,maxima_wavelengths,deg=degree)
        self.send_polynomial.emit(self.fit_polynomial)
        self.send_spectral_calibration_fit.emit(('spectral_calibration_fit',self.fit_polynomial))
        

class ChirpCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will scan the columns of the SLM with a grating stripe and record the intensity on the spectrometer.
        signals:
            - sendSpectrum : wavelength and intensity detected by the spectrometer
            - send_intensities: tuple with column index (np.1darray), wavelength axis (np.1darray) and associated spectra (np.2darray)
            - send_spectral_calibration_data: tuple, first is label 'vertical_calibration_data' and second is row and intensities tuple
            - sendProgress :  float representing the progress of the measurement.
    '''
    send_chirp= QtCore.pyqtSignal(np.ndarray,np.ndarray,np.ndarray)
    send_Chirp_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices,beam_,compression_carrier_wavelength,chirp_step,chirp_max,chirp_min):
        '''
         Initializes the Spectral beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - grating_period: (int) the vertical period (in pixels) of the phase grating
             - column_increment: (int) the step by which to shift the columns 
             - column_width: (int) the width (in pixels) of the scanned column
        ''' 
        super(ChirpCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        
        ### i dont know what to do with beam_ position
        
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.spectra = []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.Chirp=np.arange(chirp_min,chirp_max,chirp_step,dtype=int)
        #self.intensities= np.zeros((len(self.columns),len(self.wls)))# preallocate spec array
        self.intensities=[]
        self.spectral_calibration_data={
            'Chirp' : self.Chirp,
            'wavelengths' : self.wls,
            'intensities' : self.intensities
        }
        # Configure single beam over which the columns will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_beamVerticalDelimiters([0, self.SLM.get_height()])
        self.monobeam.set_beamHorizontalDelimiters([0, self.SLM.get_width()])

        self.monobeam.set_pixelToWavelength(Polynomial(1e-9*np.array([compression_carrier_wavelength,1/6])))
        self.monobeam.set_compressionCarrierWave(compression_carrier_wavelength*1e-9)        
        self.isDemo= self.SLM.write_image([0])==42 #Checks if SLM IS DEMO

        self.chirp_ = np.linspace(chirp_max,chirp_min,num=int((chirp_max-chirp_min)/chirp_step))
        # self.isDemo=False

    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
                if self.isDemo:
                    a = np.loadtxt('..\src\Chirp_dataset.txt')
                    self.wls = a[-1]
                    self.Chirp_data= a[-2]
                    for h in range(len(self.Chirp_data)):
                        if self.Chirp_data[h]==0:
                            f = h
                            break
                    self.Chirp_data = self.Chirp_data[:f]        
                    self.data = a[:-3]
                # Emit the data through signals

                    for a in range(len(self.Chirp_data)):
                        
                        self.Chirp_calibration_data={
                            'Chirp' : np.array(self.Chirp_data),
                            'wavelengths' : self.wls,
                            'data' : np.array(self.data)
                            }

                        time.sleep(0.1)
                        self.sendProgress.emit(a/len(self.Chirp_data)*100)
                        self.send_chirp.emit(np.array(self.Chirp_data[:a]),self.wls[:a],np.array(self.data[:a]))
                else:
                     self.BEAM = self.SLM['beam'][self.beam_]
                     for a in range(len(self.chirp_)):
                            
                        self.monobeam.set_currentPhase(Polynomial([0,0,self.chirp_[a]]),mode='absolute')
                        image_output=self.monobeam.makeGrating()                
                        self.SLM.write_image(image_output)
                        self.takespectrum()
                        self.intensities.append(self.spectra)
                        self.sendProgress.emit(a/len(self.chirp_)*100)
                        self.Chirp_calibration_data={
                            'Chirp' : np.array(self.chirp_),
                            'wavelengths' : self.wls,
                            'data' : np.array(self.intensities)
                            }
                        self.send_chirp.emit(np.array(self.Chirp_data[:a]),self.wls[:a],np.array(self.data[:a]))
        self.send_Chirp_calibration_data.emit(('spectral_calibration_raw_data',self.Chirp_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Spêctral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')
    def stop(self):
            self.terminate = True
            print(time.strftime('%H:%M:%S') + ' Request Stop')
    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo:
            self.sendSpectrum.emit(self.wls, self.spec)

    