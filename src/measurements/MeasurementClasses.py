"""
Measurement classes for different types of measurements. Each measurement creates a new thread that runs until the
measurement has finished or was requested to stop. Measurements can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each measurements, parameter are read from Main script and remain
until the measurement has finished.
"""

import time
import re
from PyQt5 import QtCore
import numpy as np
import logging

logger=logging.getLogger(__name__)
# Measurement to acquire one spectrum
class AcquireMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, parameter):
        super(AcquireMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True

    def run(self):
        logger.info(time.strftime('%H:%M:%S') + ' Begin single spectrum acquisition')
        try:
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(50)
                self.wls = np.array(self.spectrometer.get_wavelength())
                self.take_spectrum()
                logger.info(time.strftime('%H:%M:%S') + ' Finished')
        except Exception:
            logger.exception('Single spectrum acquisition failed')
        finally:
            """ Progress 100 is what releases measurement_busy in the main window. Emitting it here
            rather than only on success means a failed or stopped measurement no longer leaves the
            interface stuck on "devices are busy" until the software is restarted. """
            self.sendProgress.emit(100)

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        logger.info(time.strftime('%H:%M:%S') + ' Request Stop')


# Measurement to continuously view spectra
class ViewMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendClear = QtCore.pyqtSignal()

    def __init__(self, devices, parameter):
        super(ViewMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False

    def run(self):
        try:
            while not self.terminate:  # check whether stopping measurement is called
                t = time.time()
                self.sendProgress.emit(50)
                self.wls = np.array(self.spectrometer.get_wavelength())
                self.spec = np.array(self.spectrometer.get_intensities())
                self.sendClear.emit()
                self.sendSpectrum.emit(self.wls, self.spec)

                # limit too fast acquistion for computation
                if time.time() - t < 0.02:
                    time.sleep(0.02)

            # Finish measurement when loop is terminated
            logger.info(time.strftime('%H:%M:%S') + ' Finished')
        except Exception:
            logger.exception('Continuous view failed')
        finally:
            self.sendProgress.emit(100)

    def stop(self):
        self.terminate = True
        logger.info(time.strftime('%H:%M:%S') + ' Request Stop')


# Measurement to continuously acquire spectra and concatenate in DataHandling
class RunMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, devices, parameter):
        super(RunMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False

    def run(self):
        logger.info(time.strftime('%H:%M:%S') + ' Begin continuous acquisition')
        try:
            while not self.terminate:  # loop runs until requested stop
                t1 = time.time()
                self.wls = np.array(self.spectrometer.get_wavelength())
                self.spec = np.array(self.spectrometer.get_intensities())

                # send data
                self.sendSpectrum.emit(self.wls, self.spec)
                progress = 50
                self.sendProgress.emit(progress)

                # limit too fast acquistion for computation
                if time.time() - t1 < 0.02:
                    time.sleep(0.02)
            logger.info(time.strftime('%H:%M:%S') + ' Finished')
        except Exception:
            logger.exception('Continuous acquisition failed')
        finally:
            self.sendProgress.emit(100)
        return

    #  initiate controlled stop by enableing terminate statement, that is frequently queried in run code
    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + 'Request Stop')

class BackgroundMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)

    def __init__(self, devices, parameter, scans, filename, comments):
        super(BackgroundMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.summedspec = []
        self.scans = scans
        self.filename = filename[:filename.rfind('/') + 1] + 'Background'
        logger.info(filename[:filename.rfind('/') + 1] + 'Background')
        self.comments = comments
        self.terminate = False

    def run(self):
        try:
            if not self.terminate:  # check whether stopping measurement is called
                """ Wavelengths are read once, before the loop. They used to be assigned only inside
                it, so a background of a single scan emitted an empty array and broke the receiving
                slot. scans is clamped because its spin box declares no minimum and so allows 0,
                which also divided by zero below. """
                scans = max(int(self.scans), 1)
                self.wls = np.array(self.spectrometer.get_wavelength())
                self.summedspec = np.array(self.spectrometer.get_intensities())
                for i in range(scans - 1):
                    self.sendProgress.emit((i + 1) / scans * 100)
                    self.spec = np.array(self.spectrometer.get_intensities())
                    self.summedspec = self.summedspec + self.spec
                self.spec = self.summedspec / scans
                self.sendSpectrum.emit(self.wls, self.spec)
                self.sendSave.emit(self.filename, self.comments)
                logger.info(time.strftime('%H:%M:%S') + 'Background acquired')
        except Exception:
            logger.exception('Background acquisition failed')
        finally:
            self.sendProgress.emit(100)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
