"""
Calibration classes for different types of calibration. Each calibration creates a new thread that runs until the
calibration has finished or was requested to stop. Calibrations can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each calibration, parameter are read from Main script and remain
until the measurement has finished.
"""
import time
from PyQt5 import QtCore
import numpy as np
from pathlib import Path
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration
from numpy.polynomial import Polynomial as P


class VerticalBeamCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will gradually turn on rows of the SLM and record the intensity on the spectrometer.
        signals:
            - send_vertical_calibration : 2d.array of spectra acquired during the row scan
            - sendWavelengths :  array of wavelengths associated with the spectra array
            - sendIntensities : tuple of np arrays, first is row index and second is spectrally integrated intensity
            - sendProgress :  float representing the progress of the measurement.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_intensities= QtCore.pyqtSignal(np.ndarray,np.ndarray)
    send_vertical_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, grating_period,rows_multiple):
        '''
         Initializes the Vertical beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - parameters: dictonnary holding the grating period and the increment in number of activated rows.
        ''' 
        super(VerticalBeamCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        print(self.SLM.get_height())
        self.rows=np.arange(0,self.SLM.get_height(),rows_multiple)
        self.intensities= np.zeros(self.rows.shape)# preallocate spec array
        self.vertical_calibration_data={
            'rows' : self.rows,
            'intensities' : self.intensities
        }
        # Configure single beam over which the rows will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_beamVerticalDelimiters([0, self.SLM.get_height()])
        self.monobeam.set_beamHorizontalDelimiters([0, self.SLM.get_width()])
        self.monobeam.set_gratingPeriod(grating_period)

    def run(self):
        for i,row in enumerate(self.rows):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_beamVerticalDelimiters([0, row])
                image_output=self.monobeam.makeGrating()                
                self.SLM.write_image(image_output)
                self.take_spectrum()
                self.intensities[i]=np.sum(self.spec)
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class ChirpTemporalCalibration(QtCore.QThread):
    '''
        Runs a measurement that will gradually turn on rows of the SLM and record the intensity on the spectrometer.
        signals:
            - send_vertical_calibration : 2d.array of spectra acquired during the row scan
            - sendWavelengths :  array of wavelengths associated with the spectra array
            - sendIntensities : tuple of np arrays, first is row index and second is spectrally integrated intensity
            - sendProgress :  float representing the progress of the measurement.
    '''
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_intensities= QtCore.pyqtSignal(np.ndarray,np.ndarray)
    send_vertical_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, grating_period,rows_multiple):
        '''
         Initializes the Vertical beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - parameters: dictonnary holding the grating period and the increment in number of activated rows.
        ''' 
        super(ChirpTemporalCalibration, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        print(self.SLM.get_height())
        self.rows=np.arange(0,self.SLM.get_height(),rows_multiple)
        self.intensities= np.zeros(self.rows.shape)# preallocate spec array
        self.vertical_calibration_data={
            'rows' : self.rows,
            'intensities' : self.intensities
        }
        # Configure single beam over which the rows will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_beamVerticalDelimiters([0, self.SLM.get_height()])
        self.monobeam.set_beamHorizontalDelimiters([0, self.SLM.get_width()])
        self.monobeam.set_gratingPeriod(grating_period)

    def run(self):
        for i,row in enumerate(self.rows):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_beamVerticalDelimiters([0, row])
                image_output=self.monobeam.makeGrating()                
                self.SLM.write_image(image_output)
                self.take_spectrum()
                self.intensities[i]=np.sum(self.spec)
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

class ChirpTemporalCalibration_2(QtCore.QThread):
    '''
        Runs a chirp scan with stablish carrier wavelenth, a minimun value, a maximun  value and a defined step.
            - spectrum: 2d.array of spectra acquired during the chrip scan
    '''
    
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    send_intensities= QtCore.pyqtSignal(np.ndarray,np.ndarray)
    send_vertical_calibration_data = QtCore.pyqtSignal(tuple)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices,Chirp_min,Chirp_max,step,Compression_carrier_wavelength):
        '''
         Initializes the Vertical beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - parameters: dictonnary holding the grating period and the increment in number of activated rows.
        ''' 
        super(ChirpTemporalCalibration, self).__init__()
        step = int(step)
        Chirp_min = int(Chirp_min)
        Chirp_max = int(Chirp_max)
        Compression_carrier_wavelength = int(Compression_carrier_wavelength)
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        self.wavelength=np.linspace(Chirp_min,Chirp_max,num=(Chirp_max-Chirp_min/step))
        self.chirp= np.zeros(self.wavelength.shape)# preallocate spec array
        self.chirp_data={
            'wavelength' : self.wavelength,
            'chirp' : self.chirp
        }
        # Configure single beam over which the rows will be scanned
        self.bm=Beam(300,600)
        self.carrier_wavelength = Beam.set_compressionCarrierWave(Compression_carrier_wavelength)
        self.optimalPhase = self.bm.set_optimalPhase(P([0,0,Chirp_min]))


    def run(self):
        for i,row in enumerate(self.rows):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_beamVerticalDelimiters([0, row])
                image_output=self.monobeam.makeGrating()                
                self.SLM.write_image(image_output)
                self.take_spectrum()
                self.intensities[i]=np.sum(self.spec)
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')