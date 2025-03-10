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
from scipy import special
import sys
path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
from src.compute.beams import Beam
from src.compute.calibration import Calibration



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
        self.isDemo= self.SLM.write_image([0])==42 #Checks if SLM IS DEMO
        if self.isDemo:
            fakeBeamshape = lambda x,x0: 1000*(special.erf((x-x0)/10)+1)
            self.demoIntensities=fakeBeamshape(self.rows,self.SLM.get_height()/8)+fakeBeamshape(self.rows,3*self.SLM.get_height()/8)+fakeBeamshape(self.rows,5*self.SLM.get_height()/8)+fakeBeamshape(self.rows,7*self.SLM.get_height()/8)

    def run(self):
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
        print('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


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

    def __init__(self,devices,grating_period,column_increment, column_width):
        '''
         Initializes the Vertical beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - grating_period: (int) the vertical period (in pixels) of the phase grating
             - column_increment: (int) the step by which to shift the columns 
             - column_width: (int) the width (in pixels) of the scanned column
        ''' 
        super(SpectralBeamCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.spectra = []  # preallocate spec array
        self.wls = self.spectrometer.get_wavelength()
        self.terminate = False
        self.acquire_measurement = True
        self.columns=np.arange(0,self.SLM.get_width(),column_increment)
        self.column_width=column_width
        self.intensities= np.zeros((len(self.columns),len(self.wls)))# preallocate spec array
        self.spectral_calibration_data={
            'columns' : self.columns,
            'wavelengths' : self.wls,
            'intensities' : self.intensities
        }
        # Configure single beam over which the columns will be scanned
        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
        self.monobeam.set_beamVerticalDelimiters([0, self.SLM.get_height()])
        self.monobeam.set_beamHorizontalDelimiters([0, self.SLM.get_width()])
        self.monobeam.set_gratingPeriod(grating_period)
        self.isDemo= self.SLM.write_image([0])==42 #Checks if SLM IS DEMO

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
                    self.intensities[i,:]=fakeSpectrum
                    self.sendSpectrum.emit(self.wls,fakeSpectrum)
                else:
                    self.intensities[i,:]=self.spectra
                # Emit the data through signals 
                self.sendProgress.emit(i/len(self.columns)*100)
                self.spectral_calibration_data['intensities']=self.intensities
                self.send_intensities.emit(self.columns,self.wls,self.intensities)
        self.spectral_calibration_data['intensities']=self.intensities
        self.send_spectral_calibration_data.emit(('spectral_calibration_data',self.spectral_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Spêctral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo:
            self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
    def fakeSignal(self,wls,current_col,col_width):
        wave_per_pix=0.5 #Arbitrary but reasonnable parameters to simulate data acq.
        min_wave=600
        fakeSpectrum=np.zeros(wls.shape)
        for i,wave in enumerate(wls):
            if wave-min_wave<=(current_col+col_width/2)*wave_per_pix and wave-min_wave>(current_col-col_width/2)*wave_per_pix:
                fakeSpectrum[i]= 1000
        return fakeSpectrum