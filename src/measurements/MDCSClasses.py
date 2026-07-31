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

    def phase_cycling(self, j):
        '''
            Takes the eight spectra needed for the phase cycling procedure.
                - j: Iteration index of the scanned delay
        '''
        self.intensity = np.zeros(len(self.wls))
        if getattr(self, "isPhaseCycling", True):
            operations = np.array([1, -1, -1, 1, -1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1])
        else:
            operations = np.array([1])  # single step, no phase cycling

        self.cep = {
            'A':  np.array([0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi, 0, 0, 0, 0, np.pi, np.pi, np.pi, np.pi]),
            'B':  np.array([0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, np.pi]),
            'C':  np.array([0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi]),
            'LO': np.array([0, np.pi, np.pi, 0, np.pi, 0, 0, np.pi, np.pi, 0, 0, np.pi, 0, np.pi, np.pi, 0])
        }

        self.specs = []
        for i in range(len(operations)):
            image_output = None

            for name in self.beam_name:
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
                self.flag = 0
                self.take_spectrum()
            else:
                self.fake_spectrum()
            self.specs.append(self.spec.copy())
        
        # Total signal
        S_total = np.zeros_like(self.wls, dtype=complex)
        for i in range(len(operations)):
            S_total += operations[i] * self.specs[i]
        self.intensity = S_total/np.sum(np.abs(operations))

        self.sendPhaseCycling.emit(self.wls, np.abs(self.intensity))
    
    def take_spectrum(self, max_iter=10):
        '''
            Get the spectrum and check if the measurement is good. The while loop breaks if too many spectrum were took.
                - max_iter: maximum number of trials to get a good spectrum 
        '''
        count = 0
        while self.flag == 0 and count < max_iter:
            self.spec = np.array(self.spectrometer.get_intensities())
            time.sleep(0.1)
            self.sendPhaseCycling.emit(self.wls, self.spec)
            self.check_spectrum()   # updates self.flag
            count += 1
        if count == max_iter:
            logger.info('%s Measurement background changes over the tolerance threshold'%datetime.datetime.now())
            return
        if not self.isDemo:
            self.sendSpectrum.emit(self.wls, self.spec)

    def check_spectrum(self, saturation=16000, tolerance=0.005):
        '''
            Check if the spectrum is chnaging too much between different acquisitions.
                - saturation: saturation count for the camera (16000 for stresing)
                - tolerance: defines how big the change in background is still acceptable
                    example: tolerance * saturation = average change per pixel
                        0.005 x 16000 = 80
                        0.01  x 16000 = 160
        '''

        if self.prev_spec is None:
            self.prev_spec = self.spec.copy()
            self.flag = 0
            return

        delta = np.abs(self.spec - self.prev_spec)
        mean_change = np.mean(delta)
        relative_change = mean_change / saturation

        self.flag = int(relative_change < tolerance)

        self.prev_spec = self.spec.copy()
    
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