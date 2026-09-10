"""
Measurement classes for different types of measurements. Each measurement creates a new thread that runs until the
measurement has finished or was requested to stop. Measurements can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each measurements, parameter are read from Main script and remain
until the measurement has finished.
"""

import time
from PyQt5 import QtCore
import numpy as np
from numpy.polynomial.polynomial import Polynomial
from numpy.polynomial import Polynomial as P
import logging
import datetime
from scipy.interpolate import interp1d
from scipy.fft import fft, fftfreq, ifft, ifftshift, fftshift
from compute import colbertoutils as co

logger=logging.getLogger(__name__)
# Measurement to acquire one spectrum
class AcquireLO(QtCore.QThread):
    """
        Class implementing the LO acquisition.
        - sendSpectrum : wavelength and intensity detected by the spectrometer
        - sendProgress: float representing the progress of the measurement.
        - sendLOData: wavelength and intensity of the local oscillator
        - sendBeam: signal to the beam explorer
    """
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendLOData = QtCore.pyqtSignal(tuple)
    sendBeam = QtCore.pyqtSignal(object)

    def __init__(self, devices, beam_name, beam):
        '''
            Initializes the acquisition of the local oscillator spectrum.
                - devices: the devices dictionnary holding at least a spectrometer and a SLM
                - beam_name: the local oscillator beam name (LO)
                - beam: dictionnary of the local oscillator beam
        '''
        super(AcquireLO, self).__init__()
        self.terminate = False
        self.acquire_measurement = True
        self.spectrometer = devices['spectrometer']
        self.SLM = devices['SLM']
        self.LO_spectrum = []
        self.beam_name = beam_name
        self.beam = beam

    def run(self):
        '''
            Runs the spectrum acquisition.
        '''
        self.wls = self.spectrometer.get_wavelength()
        self.beam.set_currentPhase(P(np.array([0, 0])), mode='relative', unit='fs')
        self.sendBeam.emit((self.beam_name, self.beam))
        image_output = self.beam.makeGrating()
        self.SLM.write_image(image_output)

        self.LO_spectrum = np.array(self.spectrometer.get_intensities())
        self.sendProgress.emit(50)
        self.LO_spectrum = np.array(self.spectrometer.get_intensities())
        self.LO_data = {
            'spec' : self.LO_spectrum,
            'wavelengths' : self.wls,
            }
        self.sendLOData.emit(('LO_data', self.LO_data))
        self.sendSpectrum.emit(self.wls, self.LO_spectrum)
        logger.info(time.strftime('%H:%M:%S') + ' Finished')
        self.sendProgress.emit(100)
        self.terminate = True

class BoxcarGeometry(QtCore.QThread):
    '''
        Runs a MDCS measurement in the origial boxcar geometry
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
    sendPhaseCycling = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeam = QtCore.pyqtSignal(object)
    sendMDCSPlot = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    sendMDCSRaw = QtCore.pyqtSignal(tuple)
    sendSave = QtCore.pyqtSignal()
    sendFourierReal = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    sendFourierImag = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)

    def __init__(self, devices, measurement_type, t_LO, t_scanned, t_secondary, beam_name, beam, LO_spectrum, filename, comments, phase_cycling=True, demo=False):
        '''
            Initializes the semporal beam calibration measurement.
                - devices: the devices dictionnary holding at least a spectrometer and a SLM
                - measurement_type: 0Q, 1Q - rephasing, 1Q - non rephasing, 2Q
                - t_LO: delay between LO and the last light-matter interaction in fs
                - t_scanned: np.arange(delay_min, delay_max, delay_step, dtype=int) of the scanned time
                - t_secondary: np.arange(delay_min, delay_max, delay_step, dtype=int) of the secondary time
                - beam_name: all the beams name
                - beam: dictionnary of all the beams
                - delay_min: set in the GUI in fs^2
                - demo: is demo or not
        ''' 

        super(BoxcarGeometry, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM = devices['SLM']

        self.wls = self.spectrometer.get_wavelength()
        self.spectra = [] # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.measurement_type = measurement_type
        self.t_LO = t_LO
        self.t_scanned = t_scanned
        self.t_secondary = t_secondary
        self.LO_spectrum = LO_spectrum
        #self.intensities = [[] for _ in range(len(self.t_secondary))]

        # replaces: self.intensities = [[] for _ in range(len(self.t_secondary))]
        self.intensities = np.full(
            (len(self.t_secondary), len(self.t_scanned), len(self.wls)),
            np.nan,
            dtype=float
        )
        
        self.measurement_data={
            'type' : self.measurement_type,
            't_LO' : self.t_LO,
            't_scanned' : self.t_scanned,
            't_secondary' : self.t_secondary,
            'wavelengths' : self.wls,
            'LO_spectrum' : self.LO_spectrum,
            'intensities' : self.intensities
        }
        self.isPhaseCycling = phase_cycling
        self.isDemo = demo
        self.beam_name = beam_name
        self.beam = beam
        self.flag = 0
        self.prev_spec = None
        self.filename = filename[:filename.rfind('/') + 1] + 'MDCS'
        logger.info(filename[:filename.rfind('/') + 1] + 'MDCS')
        self.comments = comments

    def run(self):
        '''
            Runs the MDCS measurement and send the data in DataHandling after each iterations.
        '''
        if not self.terminate:  # check whether stopping measurement is called
            for i in range(len(self.t_secondary)):
                self.timing(i)
                for j in range(len(self.t_scanned)):
                    if not self.terminate:
                        self.phase_cycling(j)

                        self.intensities[i, j, :] = self.intensity #self.intensities[i].append(self.intensity)
                        #print(self.intensities)

                        self.measurement_data = {
                            'type' : self.measurement_type,
                            't_LO' : self.t_LO,
                            't_scanned' : self.t_scanned,
                            't_secondary' : self.t_secondary,
                            'wavelengths' : self.wls,
                            'LO_spectrum' : self.LO_spectrum,
                            'intensities' : self.intensities #np.array(self.intensities)
                        }
                        #self.sendMDCSPlot.emit(self.wls, self.t_scanned[:j+1], np.array(self.intensities[i]).T)
                        self.sendMDCSPlot.emit(self.wls, self.t_scanned[:j + 1], np.abs(self.intensities[i, :j + 1, :].T))

                        self.sendMDCSRaw.emit(('MDCS_raw_data', self.measurement_data))
                        self.sendProgress.emit(((i * len(self.t_scanned)) + (j + 1)) / (len(self.t_secondary) * len(self.t_scanned)) * 100)
                self.sendSave.emit()
        self.sendProgress.emit(100)
        self.stop()
        print(self.measurement_type+' measurement '+time.strftime('%H:%M:%S')+' finished')

    def timing(self, i):
        '''
            Defines the timming vectors for the four beams regarding the measurement type.
                - i: Iteration index of the secondary delay
        '''
        Nb_step = len(self.t_scanned)
        if self.measurement_type == '0Q':
            self.group_delay = {
                'A' : np.zeros(Nb_step),
                'C' : self.t_secondary[i]*np.ones(Nb_step),
                'B' : self.t_scanned.copy(),
                'LO' : self.t_scanned-self.t_LO*np.ones(Nb_step)
            }
        elif self.measurement_type == '1Q - rephasing':
            self.group_delay = {
                'A' : np.zeros(Nb_step),
                'C' : self.t_scanned.copy(),
                'B' : self.t_scanned+self.t_secondary[i]*np.ones(Nb_step),
                'LO' : self.t_scanned+(self.t_secondary[i]-self.t_LO)*np.ones(Nb_step)
            }
        elif self.measurement_type == '1Q - non rephasing':
            self.group_delay = {
                'C' : np.zeros(Nb_step),
                'A' : self.t_scanned.copy(),
                'B' : self.t_scanned+self.t_secondary[i]*np.ones(Nb_step),
                'LO' : self.t_scanned+(self.t_secondary[i]-self.t_LO)*np.ones(Nb_step)
            }
        elif self.measurement_type == '2Q':
            self.group_delay = {
                'C' : np.zeros(Nb_step),
                'B' : self.t_secondary[i]*np.ones(Nb_step),
                'A' : self.t_scanned+self.t_secondary[i]*np.ones(Nb_step),
                'LO' : self.t_scanned+(self.t_secondary[i]-self.t_LO)*np.ones(Nb_step)
            }
        elif self.measurement_type == 'LO scan':
            self.group_delay = {
                'C' : np.zeros(Nb_step),
                'B' : np.zeros(Nb_step),
                'A' : np.zeros(Nb_step),
                'LO' : self.t_scanned.copy()
            }
        
        # To give the right delay between pulse
        for key in self.group_delay:
            self.group_delay[key] *= -1

    def phase_cycling(self, j=None):
        '''
            Takes the eight spectra needed for the phase cycling procedure.
                - j: Iteration index of the scanned delay. Default is None and does not apply additionnal delay to the beams
        '''
        self.intensity = np.zeros(len(self.wls))
        if getattr(self, "isPhaseCycling", True):
            operations = np.array([1,-1,-1,1,-1,1,1,-1])
        else:
            operations = np.array([1])  # single step, no phase cycling

        self.cep = {
            'A':  np.pi*np.array([0,0,0,0,0,0,0,0]),
            'B':  np.pi*np.array([0,0,1,1,0,0,1,1]),
            'C':  np.pi*np.array([0,0,0,0,1,1,1,1]),
            'LO': np.pi*np.array([0,1,0,1,0,1,0,1])
        }

        self.specs = []
        for i in range(len(operations)):
            image_output = None

            for name in self.beam_name:
                if j is None:
                    self.coeffs = np.array([self.cep[name][i]])
                else:
                    self.coeffs = np.array([self.cep[name][i], self.group_delay[name][j]])
                self.beam[name].set_currentPhase(P(self.coeffs), mode='relative', unit='fs')
                beam_image = self.beam[name].makeGrating()
                if image_output is None:
                    image_output = beam_image.copy()
                else:
                    image_output += beam_image
            
            self.sendBeam.emit((self.beam))
            self.SLM.write_image(image_output)

            if not self.isDemo:
                self.spec=np.array(self.spectrometer.get_intensities())
                time.sleep(0.03)
                self.sendSpectrum.emit(self.wls, self.spec)
            else:
                self.fake_spectrum()
            self.specs.append(self.spec.copy())
        
        # Total signal
        self.heterodyne_signal= np.zeros_like(self.wls, dtype=float)
        for i in range(len(operations)):
            self.heterodyne_signal += operations[i] * self.specs[i]

        self.sendPhaseCycling.emit(self.wls, self.heterodyne_signal)
    
    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

    def fake_spectrum(self):
        t1 = time.time()
        wls = self.wls                           # 1D array
        n = len(wls)                             # number of points
        sigma = 40.0
        amplitude = 500 * 2000 / (sigma * np.sqrt(2 * np.pi))
        center = 620.0                           # Gaussian center wavelength
        gaussian = amplitude * np.exp(-((wls - center) ** 2) / (2 * sigma**2))
        noise = np.random.randint(0, 50, n)
        scaling = 0.8 + 0.2 * np.random.rand()   # random scaling factor
        spec = scaling * (noise + gaussian - 50)
        self.spec = spec.astype(float)

class PhaseCycling(QtCore.QThread):
    """
        Class defining a phase cycling procedure.
        QtCore.signals:
        - sendProgress: float representing the progress of the measurement.
        - sendSpectrum: wavelength and intensity detected by the spectrometer.
        - sendBeam: signal to the beam explorer
        - sendPhaseCycling: 

    """
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendPhaseCycling = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeams = QtCore.pyqtSignal(object)

    def __init__(self, devices, beams, demo=False):
        '''
            Initializes a phase cycling procedure 
                - devices: the devices dictionnary holding at least a spectrometer and a SLM
                - beam_name: all the beams name
                - beam: dictionnary of all the beams
                - demo: is demo or not
        ''' 

        super(PhaseCycling, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM = devices['SLM']

        self.wls = self.spectrometer.get_wavelength()
        self.spectra = [] # preallocate spec array
        self.terminate = False
        self.isDemo = demo
        self.beams = beams
        self.operations = np.array([1,-1,-1,1,-1,1,1,-1])
        self.CEPs = {
            'A':  np.pi*np.array([0,0,0,0,0,0,0,0]),
            'B':  np.pi*np.array([0,0,1,1,0,0,1,1]),
            'C':  np.pi*np.array([0,0,0,0,1,1,1,1]),
            'LO': np.pi*np.array([0,1,0,1,0,1,0,1])
        }

    def run(self):
        '''
            Takes the spectra needed for the phase cycling procedure.
        '''
        self.intensity = np.zeros(len(self.wls))
        self.specs = []
        for i in range(len(self.operations)):
            if not self.terminate:
                image_output = None
                for name in self.beams.keys():
                    self.coeffs = self.beams[name].get_currentPhase().coef
                    self.coeffs[0] = self.CEPs[name][i]
                    self.beams[name].set_currentPhase(P(self.coeffs), mode='relative', unit='fs')
                    beam_image = self.beams[name].makeGrating()
                    if image_output is None:
                        image_output = beam_image.copy()
                    else:
                        image_output += beam_image
                
                self.sendBeams.emit((self.beams))
                self.SLM.write_image(image_output)

                time.sleep(0.03)
                if not self.isDemo:
                    self.spec=np.array(self.spectrometer.get_intensities())
                else:
                    self.spec=self.fake_spectrum()
                self.sendSpectrum.emit(self.wls, self.spec)
                self.specs.append(self.spec.copy())
        
        # Total signal
        self.heterodyne_signal= np.zeros_like(self.wls, dtype=float)
        for i in range(len(self.operations)):
            self.heterodyne_signal += self.operations[i] * self.specs[i]

        self.sendPhaseCycling.emit(self.wls, self.heterodyne_signal)
        self.sendProgress.emit(100)
        self.stop()

    def fake_spectrum(self):
        """
            Returns a spectrum typical of those found in phase cycling measurements.
        """
        wls = self.wls*1e-9                           # 1D array
        freqs=co.waveToAngFreqPHz(wls)
        sigma = 0.10*np.abs(np.max(freqs)-np.min(freqs))
        amplitudes = {'A':0.2,
                      'B':0.2,
                      'C':0.2,
                      'LO':1,
                      'FWM':0.01}
        gaussian = lambda x,center,a: a * np.exp(-((x - center) ** 2) / (2 * sigma**2))
        gaussian_interf=lambda x,t,phi,center,a:gaussian(x,center,a)*np.exp(1j*(t*(x-center)+phi))
        signal=np.zeros_like(freqs,dtype=complex)
        for name in self.beams.keys():
            phi=self.beams[name].get_currentPhase().coef[0] 
            t=self.beams[name].get_currentPhase().coef[1] 
            center=self.beams[name].get_delayCarrier()
            print('Center is at %.2e PHz'%center)
            print('t and phi for beam %s is %.2f fs and %.2f rad'%(name,t,phi))
            signal = signal + gaussian_interf(freqs,t,phi,center,amplitudes[name])
        signal += signal + gaussian_interf(freqs,
                                           self.beams['C'].get_currentPhase().coef[1],
                                           self.beams['A'].get_currentPhase().coef[0]-self.beams['B'].get_currentPhase().coef[0]-self.beams['C'].get_currentPhase().coef[0]+self.beams['LO'].get_currentPhase().coef[0],
                                           center,
                                           amplitudes['FWM'])
        signal=np.abs(signal)**2

        return signal.astype(float)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
