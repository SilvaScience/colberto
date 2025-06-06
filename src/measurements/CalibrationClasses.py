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
<<<<<<< Updated upstream

=======
import time
>>>>>>> Stashed changes

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


<<<<<<< Updated upstream
class ChirpTemporalCalibration(QtCore.QThread):
=======
class ChirpCalibrationMeasurement_(QtCore.QThread):
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

    def __init__(self,devices,grating_period,compress_carrier_wv,chirp_max,chirp_min,chirp_step,column_increment, column_width):
        '''
         Initializes the Spectral beam calibration measurement
         input:
             - devices: the devices dictionnary holding at least a spectrometer and a SLM
             - grating_period: (int) the vertical period (in pixels) of the phase grating
             - column_increment: (int) the step by which to shift the columns 
             - column_width: (int) the width (in pixels) of the scanned column
        ''' 
        super(ChirpCalibrationMeasurement_, self).__init__()
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
        self.monobeam.set_beamVerticalDelimiters([0, self.SLM.get_height()])
        self.monobeam.set_beamHorizontalDelimiters([0, self.SLM.get_width()])
        self.monobeam.bm.set_pixelToWavelength(P(1e-9*np.array([500,1/6])))
        self.monobeam.set_compressionCarrierWave(self.compress_carrier_wv*1e-9)
        self.monobeam.set_gratingPeriod(grating_period)
        self.isDemo= self.SLM.write_image([0])==42 #Checks if SLM IS DEMO

    def run(self):
        for chirp_val in enumerate(self.chirp):
            if not self.terminate:  # check whether stopping measurement is called
                #Take the data
                self.monobeam.set_currentPhase(P([0,0,chirp_val]),mode='absolute')
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
        print('Spêctral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        if not self.isDemo:
            self.sendSpectrum.emit(self.wls, self.spec)
    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
    def fakeSignal(self,wls,current_col,col_width):
        wave_per_pix=0.1 #Arbitrary but reasonnable parameters to simulate data acq.
        min_wave=600
        fakeSpectrum=np.zeros(wls.shape)
        for i,wave in enumerate(wls):
            if wave-min_wave<=(current_col+col_width/2)*wave_per_pix and wave-min_wave>(current_col-col_width/2)*wave_per_pix:
                fakeSpectrum[i]= 1000
        fakeSpectrum=fakeSpectrum+10*np.random.rand(len(fakeSpectrum))
        return fakeSpectrum

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

        
        self.isDemo= self.SLM.write_image([0])==42 #Checks if SLM IS DEMO
        

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
                    self.Chirp_data.append(self.Chirp_)
                # Emit the data through signals

                    for a in range(len(self.Chirp_data)):
                        self.sendProgress.emit(h/len(self.Chirp_data)*100)
                        self.Chirp_calibration_data={
                            'Chirp' : np.array(self.Chirp_data[a]),
                            'wavelengths' : self.wls[a],
                            'data' : np.array(self.data[a])
                            }

                        time.sleep(0.05)
                        self.send_chirp.emit(np.array(self.Chirp_data[:a]),self.wls[:a],np.array(self.data[:a]))
                else:
                    chirp_ = np.linspaceI(self.chirp_max,self.chirp_min,num=(self.chirp_max-self.chirp_min)/self.chirp_step)
                    for a in range(len(chirp_)):
                            
                        self.monobeam=Beam(self.SLM.get_width(),self.SLM.get_height())
                        self.monobeam.set_pixelToWavelength(P(1e-9*np.array([500,1/6])))
                        self.monobeam.set_compressionCarrierWave(self.compression_carrier_wavelength*1e-9)
                        
            
                        image_output=self.monobeam.makeGrating()                
                        self.SLM.write_image(image_output)
                        self.take_spectrum()
        self.send_Chirp_calibration_data.emit(('spectral_calibration_raw_data',self.Chirp_calibration_data))
        self.sendProgress.emit(100)
        self.stop()
        print('Spêctral Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')
    def stop(self):
            self.terminate = True
            print(time.strftime('%H:%M:%S') + ' Request Stop')
    

    
class SpectralBeamCalibrationMeasurement(QtCore.QThread):
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                self.sendProgress.emit(i/len(self.rows)*100)
                self.vertical_calibration_data['intensities']=self.intensities
                self.send_intensities.emit(self.rows,self.intensities)
        self.vertical_calibration_data['intensities']=self.intensities
        self.send_vertical_calibration_data.emit(('vertical_calibration_data',self.vertical_calibration_data))
=======
                self.sendProgress.emit(i/len(self.columns)*100)
                self.spectral_calibration_data={
                    'columns' : np.array(self.columns_out),
                    'wavelengths' : self.wls,
                    'data' : np.array(self.intensities)
                }
                self.send_intensities.emit(np.array(self.columns_out),self.wls,np.array(self.intensities))
                
        self.send_spectral_calibration_data.emit(('spectral_calibration_raw_data',self.spectral_calibration_data))
>>>>>>> Stashed changes
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