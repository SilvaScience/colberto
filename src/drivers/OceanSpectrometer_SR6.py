# -*- coding: utf-8 -*-
"""
Created on Wed Jan  18 13:26:53 2023

@author: David Tiede
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

Based on pyseabreeze (c) A Poehlmann. Unfortunately, some features such as direct binning and averaging in spectrometer
is not implemented and performed manually in this file.

 TODO:
 implement acquiring method in which interface is waiting for new spectrum
"""
import numpy as np
import sys
from PyQt5 import QtCore
import time
from collections import defaultdict
import threading
from datetime import datetime

import seabreeze
# Choose only one backend. For Ocean SR6 typically "pyseabreeze" works.
# Remove the conflicting double calls to seabreeze.use(...)
seabreeze.use("pyseabreeze")
from seabreeze.spectrometers import Spectrometer


from threading import Lock
usb_lock = Lock()  # <-- ADD THIS (global lock at top of file, only once)

class OceanSpectrometer(QtCore.QThread):
    name = "OceanSpectrometer"
    type = "Spectrometer"

    def __init__(self):
        super(OceanSpectrometer, self).__init__()

        # worker thread that continuously talks to the device
        self.spectrometer = OceanSpectrometerWorker()
        self.spectrometer.sendSpectrum.connect(self.update_spectrum)
        self.spectrometer.start()

        # wait a short time for the worker to finish initialization (non-blocking)
        # If wavelengths aren't ready yet, fallback to empty arrays but we wait only briefly.
        start = time.time()
        while (
                (not hasattr(self.spectrometer, "wavelengths"))
                or getattr(self.spectrometer, "wavelengths") is None
                or len(getattr(self.spectrometer, "wavelengths")) == 0
        ) and time.time() - start < 1.0:
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.01)

        self.wavelength = getattr(self.spectrometer, "wavelengths", np.array([]))
        self.spectrum = np.ndarray([])
        self.speclength = getattr(self.spectrometer, "speclength", 0)
        self.binnedspec = np.zeros(self.speclength) if self.speclength else np.zeros(1)
        self.int_time = 500
        self.binning = 1
        self.avg_scan = 1
        self.new_spectrum = False
        self.probe_trigger = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        self.stop = False
        self.parameter_dict["int_time"] = 500
        self.parameter_dict["binning"] = 1
        self.parameter_dict["avg_scan"] = 1

        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict["int_time"]["val"] = 500
        self.parameter_display_dict["int_time"]["unit"] = " ms"
        self.parameter_display_dict["int_time"]["max"] = 10000
        self.parameter_display_dict["int_time"]["read"] = False
        self.parameter_display_dict["binning"]["val"] = 1
        self.parameter_display_dict["binning"]["unit"] = " px"
        self.parameter_display_dict["binning"]["max"] = 20
        self.parameter_display_dict["binning"]["read"] = False
        self.parameter_display_dict["avg_scan"]["val"] = 1
        self.parameter_display_dict["avg_scan"]["unit"] = " scan(s)"
        self.parameter_display_dict["avg_scan"]["max"] = 1000
        self.parameter_display_dict["avg_scan"]["read"] = False

        # set parameter once to initialize in worker
        self.set_parameter("int_time", self.parameter_dict["int_time"])

    def set_parameter(self, parameter, value):
        if parameter == "int_time":
            self.parameter_dict["int_time"] = value
            # call worker's setter (thread-safe lock inside worker)
            self.spectrometer.set_int_time(value)
            self.int_time = value
            self.new_spectrum = False
        elif parameter == "binning":
            self.parameter_dict["binning"] = value
            self.binning = int(value)
        elif parameter == "avg_scan":
            self.parameter_dict["avg_scan"] = value
            self.avg_scan = int(value)

    def update_spectrum(self, spec, int_time):
        # slot connected to worker's sendSpectrum
        if int_time == self.int_time:
            self.spectrum = spec
            self.new_spectrum = True

    def get_wavelength(self):
        return self.wavelength

    def get_intensities(self):
        if self.avg_scan == 1:
            # wait for new spectrum with a timeout to avoid infinite loop
            wait_start = time.time()
            while not self.new_spectrum and time.time() - wait_start < 2.0:
                time.sleep(0.01)
            spectrum = self.spectrum.copy()
            self.new_spectrum = False
        else:
            spectrum = np.zeros(len(self.spectrum))
            for i in range(self.avg_scan):
                time.sleep(self.int_time / 1000.0 + 0.05)
                wait_start = time.time()
                while not self.new_spectrum and time.time() - wait_start < 2.0:
                    time.sleep(0.01)
                spectrum = spectrum + self.spectrum
                self.new_spectrum = False

        spectrum = self.do_binning(spectrum)
        time.sleep(0.005)
        return spectrum

    def do_binning(self, spectrum):
        if len(spectrum) != len(self.wavelength):
            # safety check
            self.binnedspec = np.zeros_like(spectrum)
        else:
            self.binnedspec = np.zeros_like(spectrum)
            for i in range(len(self.wavelength)):
                start = max(0, i - (self.binning - 1))
                end = min(self.speclength, i + self.binning)
                self.binnedspec[i] = np.sum(spectrum[start:end])
            denom = np.maximum(1, (2 * (self.binning - 1) + 1))
            self.binnedspec = self.binnedspec / denom / max(1, self.avg_scan)
        return self.binnedspec

    def close(self):
        try:
            self.spectrometer.close()
        except Exception:
            pass



class OceanSpectrometerWorker(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
    sendSave = QtCore.pyqtSignal()

    def __init__(self):
        super(OceanSpectrometerWorker, self).__init__()
        self.spec = None
        self.speclength = 0
        self.spec_range = None
        self.wavelengths = np.array([])
        self.change_int_time = False
        self.change_settings = False
        self.stop = False
        self.spectrum = np.zeros(1)
        self.int_time = 500  # ms
        self.binning = 1
        self.avg_scans = 1
        self.curr_int_time = 0
        self.last_acquisition_time = time.time()

        # --- Initialization Block ---
        try:
            with usb_lock:  # <-- only one thread should talk to DLL
                self.spec = Spectrometer.from_first_available()
                time.sleep(0.3)

                # Initialize firmware buffers (SR6-specific)
                try:
                    _ = self.spec.wavelengths()
                    self.spec.integration_time_micros(10000)
                    _ = self.spec.intensities()
                except Exception as e:
                    print(f"[WARN] Initial read failed but continuing: {e}")
                    time.sleep(0.2)

            model_name = str(self.spec.model)
            print(f"[INFO] Spectrometer {model_name} loaded")

            wavelengths = np.asarray(self.spec.wavelengths())
            self.speclength = len(wavelengths)
            self.spec_range = np.r_[0:self.speclength]
            self.wavelengths = wavelengths[self.spec_range]
            self.spectrum = np.zeros(self.speclength)

        except Exception as e:
            print(f"[ERROR] Could not open spectrometer: {e}")
            self.spec = None
        # --- End Initialization Block ---

    def run(self):
        """Main acquisition loop with USB lock safety."""
        while not self.stop:
            # try reopen if disconnected
            if self.spec is None:
                try:
                    with usb_lock:
                        self.spec = Spectrometer.from_first_available()
                        wavelengths = np.asarray(self.spec.wavelengths())
                        self.speclength = len(wavelengths)
                        self.spec_range = np.r_[0:self.speclength]
                        self.wavelengths = wavelengths[self.spec_range]
                        self.spectrum = np.zeros(self.speclength)
                        print("[INFO] Reopened spectrometer")
                except Exception as e:
                    print(f"[WARN] reopen failed: {e}")
                    time.sleep(1.0)
                    continue

            # enforce acquisition rate
            if time.time() - self.last_acquisition_time < 0.05:
                time.sleep(0.05)
            self.last_acquisition_time = time.time()

            # handle pending integration time safely
            if self.change_int_time:
                try:
                    with usb_lock:
                        self.spec.integration_time_micros(int(self.int_time * 1000))
                        self.curr_int_time = self.int_time
                except Exception as e:
                    print(f"[WARN] setting int time failed: {e}")
                finally:
                    self.change_int_time = False

            # safely read intensities
            try:
                with usb_lock:
                    intens = np.array(self.spec.intensities(), dtype=float)
                if self.spec_range is not None:
                    self.spectrum = intens[self.spec_range]
                else:
                    self.spectrum = intens

                self.sendSpectrum.emit(self.spectrum.copy(), self.curr_int_time)

            except Exception as e:
                print(f"[ERROR] read failed: {e}")
                try:
                    with usb_lock:
                        if self.spec:
                            self.spec.close()
                except Exception:
                    pass
                self.spec = None
                time.sleep(0.5)
                continue

            # small CPU sleep
            time.sleep(0.01)

        # clean shutdown
        try:
            with usb_lock:
                if self.spec:
                    self.spec.close()
        except Exception:
            pass

    def close(self):
        self.stop = True
        self.wait(1000)
        try:
            with usb_lock:
                if self.spec:
                    self.spec.close()
        except Exception:
            pass

    def set_int_time(self, int_time):
        self.int_time = int_time
        self.change_int_time = True




# # --- inside your module replace the worker class with this safe version ---
#
# class OceanSpectrometerWorker(QtCore.QThread):
#     # worker to continuously receive spectra from spectrometer. Pauses acquisition when settings are changed.
#     sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
#     sendSave = QtCore.pyqtSignal()
#     ready = QtCore.pyqtSignal()  # emitted once initialization succeeded
#
#     def __init__(self):
#         super(OceanSpectrometerWorker, self).__init__()
#         self.lock = threading.Lock()
#         self.spec = None
#         self.speclength = 0
#         self.spec_range = None
#         self.wavelengths = np.array([])
#         self.change_int_time = False
#         self.change_settings = False
#         self.stop = False
#         self.spectrum = np.zeros(1)
#         self.int_time = 500  # ms
#         self.binning = 1
#         self.avg_scans = 1
#         self.curr_int_time = 0
#         self.last_acquisition_time = time.time()
#
#         # DON'T open hardware here. Keep __init__ lightweight and thread-safe.
#
#     def initialize_device(self):
#         """Attempt to open the spectrometer and populate worker fields.
#            Called from run() (inside the worker thread)."""
#         try:
#             self.spec = Spectrometer.from_first_available()
#
#             # small stabilization
#             time.sleep(0.3)
#
#             # dummy read to prime firmware buffers (safe guarded)
#             try:
#                 _ = self.spec.wavelengths()
#                 self.spec.integration_time_micros(10000)  # 10 ms dummy exposure
#                 _ = self.spec.intensities()
#             except Exception as e:
#                 # non-fatal; continue after a short pause
#                 print(f"[WARN] Initial read failed but continuing: {e}")
#                 time.sleep(0.2)
#
#             model_name = str(self.spec.model)
#             print(f"[INFO] Spectrometer {model_name} loaded (worker thread)")
#
#             wavelengths = np.asarray(self.spec.wavelengths())
#             self.speclength = len(wavelengths)
#             self.spec_range = np.r_[0:self.speclength]
#             self.wavelengths = wavelengths[self.spec_range]
#             self.spectrum = np.zeros(self.speclength)
#
#             # mark ready for main thread to pick up wavelengths
#             self.curr_int_time = self.int_time
#             self.ready.emit()
#             return True
#
#         except Exception as e:
#             print(f"[ERROR] Could not open spectrometer in worker: {e}")
#             # ensure spec is None so run() will retry
#             try:
#                 if self.spec:
#                     self.spec.close()
#             except Exception:
#                 pass
#             self.spec = None
#             return False
#
#     def run(self):
#         # main acquisition loop
#         # Try to initialize device inside the thread loop (retries allowed)
#         initialized = False
#         while not self.stop and not initialized:
#             initialized = self.initialize_device()
#             if not initialized:
#                 # retry after short delay
#                 time.sleep(0.5)
#
#         # If stop requested during initialization, exit
#         if self.stop:
#             try:
#                 if self.spec:
#                     self.spec.close()
#             except Exception:
#                 pass
#             return
#
#         # Main acquisition loop
#         while not self.stop:
#             if self.spec is None:
#                 # try to reopen (transient failure recovery)
#                 if not self.initialize_device():
#                     time.sleep(0.5)
#                     continue
#
#             # rate limit
#             if time.time() - self.last_acquisition_time < 0.05:
#                 time.sleep(0.05)
#             self.last_acquisition_time = time.time()
#
#             # apply pending integration time change in a thread-safe way
#             if self.change_int_time:
#                 with self.lock:
#                     try:
#                         # SeaBreeze: integration_time_micros expects microseconds
#                         self.spec.integration_time_micros(int(self.int_time * 1000))
#                         self.curr_int_time = self.int_time
#                     except Exception as e:
#                         print(f"[WARN] setting int time failed: {e}")
#                     finally:
#                         self.change_int_time = False
#
#             # read intensities in safe block; wrap in try to avoid uncaught Python exceptions
#             try:
#                 with self.lock:
#                     intens = np.asarray(self.spec.intensities())
#                 if self.spec_range is not None:
#                     self.spectrum = intens[self.spec_range].astype(float)
#                 else:
#                     self.spectrum = intens.astype(float)
#                 # emit
#                 self.sendSpectrum.emit(self.spectrum.copy(), self.curr_int_time)
#             except Exception as e:
#                 print(f"[ERROR] read failed: {e}")
#                 try:
#                     if self.spec:
#                         self.spec.close()
#                 except Exception:
#                     pass
#                 self.spec = None
#                 time.sleep(0.2)
#                 continue
#
#             # small sleep to avoid CPU spin
#             time.sleep(0.005)
#
#         # loop ended; close device cleanly
#         try:
#             if self.spec:
#                 self.spec.close()
#         except Exception:
#             pass
#
#     def close(self):
#         self.stop = True
#         # wait for up to 1 second for thread to exit cleanly
#         self.wait(1000)
#         try:
#             if self.spec:
#                 self.spec.close()
#         except Exception:
#             pass
#
#     def set_int_time(self, int_time):
#         with self.lock:
#             self.int_time = int_time
#             self.change_int_time = True


# class OceanSpectrometerWorker(QtCore.QThread):
#     # worker to continuously receive spectra from spectrometer. Pauses acquisition when settings are changed.
#     sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
#     sendSave = QtCore.pyqtSignal()
#
#     def __init__(self):
#         super(OceanSpectrometerWorker, self).__init__()
#         self.lock = threading.Lock()
#         self.spec = None
#         self.speclength = 0
#         self.spec_range = None
#         self.wavelengths = np.array([])
#         self.change_int_time = False
#         self.change_settings = False
#         self.stop = False
#         self.spectrum = np.zeros(1)
#         self.int_time = 500  # ms
#         self.binning = 1
#         self.avg_scans = 1
#         self.curr_int_time = 0
#         self.last_acquisition_time = time.time()
#
#         # initialize the device inside init and protect with try/except
#         try:
#             self.spec = Spectrometer.from_first_available()
#
#             # --- SR6 stabilization block ---
#             # Allow USB handshake & internal buffer setup
#             time.sleep(0.3)
#
#             # Perform a dummy read sequence to initialize firmware buffers
#             try:
#                 _ = self.spec.wavelengths()
#                 self.spec.integration_time_micros(10000)  # 10 ms dummy exposure
#                 _ = self.spec.intensities()
#             except Exception as e:
#                 print(f"[WARN] Initial read failed but continuing: {e}")
#                 time.sleep(0.2)  # small pause before proceeding
#             # --- end stabilization block ---
#
#             model_name = str(self.spec.model)
#             print(f"[INFO] Spectrometer {model_name} loaded")
#
#             wavelengths = np.asarray(self.spec.wavelengths())
#             self.speclength = len(wavelengths)
#             self.spec_range = np.r_[0:self.speclength]
#             self.wavelengths = wavelengths[self.spec_range]
#             self.spectrum = np.zeros(self.speclength)
#
#         except Exception as e:
#             print(f"[ERROR] Could not open spectrometer: {e}")
#             self.spec = None
#
#     def run(self):
#         # main acquisition loop
#         while not self.stop:
#             # lazy re-open if spec is None (attempt recovery)
#             if self.spec is None:
#                 try:
#                     self.spec = Spectrometer.from_first_available()
#                     wavelengths = np.asarray(self.spec.wavelengths())
#                     self.speclength = len(wavelengths)
#                     self.spec_range = np.r_[0:self.speclength]
#                     self.wavelengths = wavelengths[self.spec_range]
#                     self.spectrum = np.zeros(self.speclength)
#                     print("[INFO] Reopened spectrometer")
#                 except Exception:
#                     # wait and retry
#                     time.sleep(0.5)
#                     continue
#
#             # avoid too-fast acquisitions
#             if time.time() - self.last_acquisition_time < 0.05:
#                 time.sleep(0.05)
#             self.last_acquisition_time = time.time()
#
#             # apply pending integration time change in a thread-safe way
#             if self.change_int_time:
#                 with self.lock:
#                     try:
#                         # SeaBreeze: integration_time_micros expects microseconds
#                         self.spec.integration_time_micros(int(self.int_time * 1000))
#                         self.curr_int_time = self.int_time
#                     except Exception as e:
#                         print(f"[WARN] setting int time failed: {e}")
#                     finally:
#                         self.change_int_time = False
#
#             # read intensities in safe block; wrap in try to avoid uncaught Python exceptions
#             try:
#                 with self.lock:
#                     # prefer high-level API intensities()
#                     intens = np.asarray(self.spec.intensities())
#                 if self.spec_range is not None:
#                     # limit to spec_range if available
#                     self.spectrum = intens[self.spec_range].astype(float)
#                 else:
#                     self.spectrum = intens.astype(float)
#
#                 # emit the spectrum with the current integration time
#                 self.sendSpectrum.emit(self.spectrum.copy(), self.curr_int_time)
#
#             except Exception as e:
#                 # many low-level C errors will still crash; but on Python exceptions we'll log and try to recover
#                 print(f"[ERROR] read failed: {e}")
#                 # attempt small delay then try re-opening the device next loop
#                 try:
#                     if self.spec:
#                         self.spec.close()
#                 except Exception:
#                     pass
#                 self.spec = None
#                 time.sleep(0.2)
#                 continue
#
#             # small sleep to avoid starving CPU
#             time.sleep(0.005)
#
#         # loop ended; close device
#         try:
#             if self.spec:
#                 self.spec.close()
#         except Exception:
#             pass
#
#     def close(self):
#         self.stop = True
#         self.wait(1000)
#         try:
#             if self.spec:
#                 self.spec.close()
#         except Exception:
#             pass
#
#     def set_int_time(self, int_time):
#         with self.lock:
#             self.int_time = int_time
#             self.change_int_time = True
