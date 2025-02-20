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



class VerticalBeamCalibrationMeasurement(QtCore.QThread):
    '''
        Runs a measurement that will gradually turn on rows of the SLM and record the intensity on the spectrometer.
    '''
    sendSpectrum= QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendIntensities= QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    add_calibration = QtCore.pyqtSignal(tuple)

    def __init__(self,devices, parameters,calibration):
        super(VerticalBeamCalibrationMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM= devices['SLM']
        self.rows= []  # preallocate indices array
        self.spec = []  # preallocate spec array
        self.intensities= []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.rows_multiple=parameters['rows_multiple']
        self.rows=np.arange(0,self.SLM.get_height(),self.rows_multiple)
        beam=Beam(parameters:while)

    def run(self):
        for i,row in enumerate(self.rows):
            if not self.terminate:  # check whether stopping measurement is called
                
                self.take_spectrum()
                self.intensities.append(np.sum(self.spec))
                self.sendProgress.emit(i/len(rows))
        self.sendIntensities.emit(self.rows,self.intensities)
        self.stop()
        print('Vertical Calibration Measurement '+time.strftime('%H:%M:%S') + ' Finished')

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

