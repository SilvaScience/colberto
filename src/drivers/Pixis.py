# -*- coding: utf-8 -*-
"""
Created on Mon Apr  28 15:09:53 2025

@author: David Tiede
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

NOTE:
Communication with Pixis is kind of slow (150ms), such that in the current interface a new image is acquired every 150ms
at the fastest. If ever a faster acquisition is required, transfer of multiple frames per communication (eg. with
cam.grab - see manual or pylablib homepage) can be implemented. For the current planned experiments an acquistion rate of
150ms was judged to be sufficient.
To install driver, picam needs to be installed on the PC. It is freely available at:
https://www.teledynevisionsolutions.com/products/pi_max4/?vertical=tvs-princeton-instruments&segment=tvs&aQ=Picam&aPage=1&dlQ=picam&dlPage=1

"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
from pylablib.devices import PrincetonInstruments
import logging
import time
import datetime
import re

logger = logging.getLogger(__name__)
class Pixis(QtCore.QThread):

    name = 'Pixis'
    
    def __init__(self, hardware_params):
        super(Pixis, self).__init__()

        #self.camera.start()
        self.wavelength = np.linspace(200,1000,1024) # get property from Worker
        self.px0 = np.linspace(1,1024,1024)
        self.spec_length = 1024 #(252,1024) # get property from Worker
        self.image = np.zeros(self.spec_length)
        self.hardware_params = hardware_params
        # Indicate shutter, required to discriminate between different detectors
        self.shutter = True

        # Parameters. Defines parameters that are required for by the interface
        self.avg_scan = 1
        self.int_time = 100
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['int_time']['val'] = self.int_time
        self.parameter_display_dict['int_time']['unit'] = ' ms'
        self.parameter_display_dict['int_time']['max'] = 10000
        self.parameter_display_dict['int_time']['read'] = False
        self.parameter_display_dict['avg_scan']['val'] = 1
        self.parameter_display_dict['avg_scan']['unit'] = ' scan(s)'
        self.parameter_display_dict['avg_scan']['max'] = 1000
        self.parameter_display_dict['avg_scan']['read'] = False
        self.parameter_display_dict['sensor_T']['val'] = 1
        self.parameter_display_dict['sensor_T']['unit'] = ' celsius'
        self.parameter_display_dict['sensor_T']['min'] = -100
        self.parameter_display_dict['sensor_T']['max'] = 100
        """ A reading, not a setting: set_parameter() has no branch for it, and the worker is what
        updates it. Declaring it writable put it among the parameters the updater does not poll, so
        the temperature on screen never changed after startup. """
        self.parameter_display_dict['sensor_T']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']


        """ Vertical readout configuration.
        The sensor is 2D: the horizontal axis is wavelength, the vertical axis is position along the
        spectrograph entrance slit. Reading a single row therefore only samples one height in the slit
        and discards the signal collected on every other row.
        set_binned_roi() sums rows ON CHIP (charge is summed before the readout amplifier), so the read
        noise is paid once instead of once per row. That is what makes weak signals usable.
        Defaults come from hardware_params so each setup can record its own alignment. """

        # initialize camera
        self.worker = CameraWorker(self.hardware_params,self.int_time)
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.sendTemperature.connect(self.update_temperature)
        self.worker.start()
        self.roi_y0=self.worker.roi_y0
        self.roi_height=self.worker.roi_height
        self.roi_binning=self.worker.roi_binning


    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.worker.set_new_integration_time(value)
            self.int_time = value
        elif parameter == 'avg_scan':
            value=int(value)
            self.parameter_dict['avg_scan'] = value
            self.worker.set_new_avg_scan(value)
            self.avg_scan = value


    def update_spectrum(self, spec):
        """This is the slot function for the sendSpectrum pyqt.signal from the worker."""
        self.spectrum = spec
        self.new_spectrum = True
        self.acquiring = False

    def get_wavelength(self):
        """This simply returns the wavelength. In Colbert this needs to be adapted if the calibration
         changes. This function will be accessible from MeasurementClasses. """
        self.calculate_wavelength_array()
        return self.wavelengths

    def calculate_wavelength_array(self):
        """
        Calculate the wavelength array for a PIXIS camera on SP-2150 spectrograph.

        Parameters:

        Returns:
            wavelengths: 1D numpy array of wavelengths (nm)
        """
        if self.monochromator is not None:
            self.center_wavelength=self.monochromator.get_monochromator_parameters()[0]
            self.grating_index=self.monochromator.get_grating_indices()[0]
        if self.hardware_params['calibrated']:

            wl_center = self.center_wavelength
            m_order = 1
            px = self.px0
            grating_key=str(self.grating_index)
            # calibration from notebook
            f=self.hardware_params[grating_key]['f']
            delta=self.hardware_params[grating_key]['delta']
            gamma=self.hardware_params[grating_key]['gamma']
            n0=self.hardware_params[grating_key]['n0']
            offset_adjust=self.hardware_params[grating_key]['offset_adjust']
            d_grating=self.hardware_params[grating_key]['d_grating']
            x_pixel=self.hardware_params[grating_key]['x_pixel']
            curvature=self.hardware_params[grating_key]['curvature']

            n = px - (n0 + offset_adjust * wl_center)

            psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
            eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))

            self.wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
        else:
            pixel_size_mm =self.hardware_params[grating_key]['pixel_size_mm'] 
            focal_length_mm = self.hardware_params[grating_key]['focal_length_mm']
            num_pixels = self.hardware_params[grating_key]['num_pixels']

            # Calculate linear dispersion (nm/mm)
            dispersion = 1e6 / (focal_length_mm * self.grating_lines_per_mm)

            # Center pixel
            center_pixel = num_pixels // 2

            # Pixel index array
            pixel_indices = np.arange(num_pixels)

            # Wavelength at each pixel
            self.wavelengths = self.center_wavelength + (pixel_indices - center_pixel) * dispersion * pixel_size_mm

    def attach_to_monochromator(self,monochromator):
        """
            Attaches the camera to a monochromator, letting the camera interface know where to get the monochromator parameters from.
            input:
                - monochromator (Monochromator QThread): The interface to the monochromator
        """
        self.monochromator=monochromator
        self.type='Spectrometer'
        self.hardware_params.update(self.monochromator.get_hardware_parameters('Pixis'))
    
    def set_roi(self, y0, height, binning=None, restart=True):
        """
            Sets the vertical region of the sensor that is read out, and how many of its rows are
            summed on chip.
            input:
                - y0 (int): index of the first sensor row to read
                - height (int): number of sensor rows covered by the region
                - binning (int, default None): number of rows summed on chip. None means sum the whole
                  region into a single row (the high signal-to-noise mode used for measurements).
                  Pass 1 to keep every row separate (the 2D mode used for alignment).
                - restart (bool, default True): restart continuous acquisition if it was running (NOT REQUIRED ANYMORE.)
            output:
                - dict: the region of interest actually applied
        """
        self.roi_y0=y0
        self.roi_height=height
        self.roi_binning=binning
        roi=self.worker.set_roi_parameters(y0, height, binning=binning, restart=True)
        return roi

    def set_binned_roi(self, y0, height):
        """
            Measurement mode: sum `height` sensor rows starting at `y0` into a single row on chip.
            input:
                - y0 (int): index of the first sensor row of the signal
                - height (int): number of rows the signal spans
        """
        return self.set_roi(y0, height, binning=height)

    def set_full_frame(self):
        """
            Alignment mode: read every sensor row separately, giving the full 2D image.
            Slower and noisier per row, but shows where the signal actually sits on the slit.
        """
        return self.set_roi(0, self.sensor_height, binning=1)

    def get_roi(self):
        """
            Returns the currently applied vertical readout configuration.
            output:
                - tuple (y0, height, binning)
        """
        return self.roi_y0, self.roi_height, self.roi_binning

    def acquisition_running(self):
        """
            Whether the camera itself considers an acquisition to be running. Falls back to the
            worker flag if the driver does not expose the query.
        """
        return self.acquiring

    def start_acquisition(self):
        """
            Sets camera to perform an acquisition
        """
        self.worker.acquiring = True
        self.acquiring = True

    def stop_acquisition(self):
        """
            Disable continuous acquisition mode of camera.
        """
        self.worker.acquiring = False
        self.acquiring = False

    def get_intensities(self):
        """
         Starts an acquisition with the provided parameters and waits for the camera to be done before returning the spectrum
        """
        self.start_acquisition()
        self.new_spectrum = False
        while not self.new_spectrum:
            time.sleep(5e-3)
        """ The camera returns one row per binning group: a single row in binned (measurement) mode,
        every sensor row in full frame (alignment) mode. Any remaining rows are summed here so both
        modes hand back a 1D spectrum. Counts therefore scale with the number of rows summed, which
        matters when comparing a spectrum to a background taken with a different region. """
        spectrum = np.asarray(self.spectrum)
        if spectrum.ndim > 1:
            spectrum = spectrum.sum(axis=0)
        return spectrum

    def update_temperature(self, temperature):
        self.parameter_dict['sensor_T'] = temperature
        self.parameter_display_dict['sensor_T']['val'] = temperature


class CameraWorker(QtCore.QThread):
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
    sendTemperature = QtCore.pyqtSignal(float)

    def __init__(self,hardware_params,int_time):
        super(CameraWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        # initialize camera interface
        self.camera = PrincetonInstruments.PicamCamera()
        self.camera.open()
        logger.info('%s Pixis succesfully initialized'%(datetime.datetime.now()))
        self.spec_length = 1024
        self.hardware_params=hardware_params
        self.change_int_time = False
        self.next_avg_scans = 1 
        self.change_avg_scans = False 
        self.spectrum = np.zeros(self.spec_length)
        self.int_time = int_time
        self.binning = 2
        self.avg_scans = 1
        self.terminate = False
        self.acquiring = False
        # Determine the number of sensor rows available for vertical binning.
        # The PIXIS used here is 1024 x 256, but ask the camera rather than assume.
        self.sensor_height = int(self.hardware_params.get('sensor_height', 256))
        try:
            detector_size = self.camera.get_detector_size()  # (width, height)
            if detector_size is not None and len(detector_size) == 2:
                self.sensor_height = int(detector_size[1])
        except Exception as e:
            logger.warning(f'Pixis: could not query detector size, assuming {self.sensor_height} rows. {e}')
        self.roi_y0 = int(self.hardware_params.get('roi_y0', 0))
        self.roi_height = int(self.hardware_params.get('roi_height', self.sensor_height))
        self.roi_binning = int(self.hardware_params.get('roi_binning', self.roi_height))
        self.set_roi_parameters(self.roi_y0, self.roi_height, self.roi_binning)
        self.set_roi()
        # set int time once
        self.camera.set_attribute_value("Exposure Time", float(self.int_time))

    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        while not self.terminate: #infinite loop
            if self.acquiring:
                self.camera.stop_acquisition()
                self.camera.read_newest_image() #Clears the sensor before proceeding with the acquisition
                frame = 0
                while frame < self.avg_scans:
                    self.camera.start_acquisition()
                    latest_image = None
                    while not type(latest_image) == np.ndarray:
                        time.sleep(1e-3)
                        latest_image = self.camera.read_newest_image()# read_newest_image() returns None when nothing arrived before the deadline above.
                    self.camera.stop_acquisition()
                    if frame == 0:
                        image = latest_image
                    else:
                        image = image + latest_image
                    frame =  frame + 1
                image=image/frame
                if isinstance(image, np.ndarray):
                    self.sendSpectrum.emit(image, self.int_time)
                    self.acquiring =  False
            else:
                time.sleep(1e-3)
            if self.new_roi:
                self.set_roi()
            if self.change_int_time:
                self.camera.set_attribute_value("Exposure Time", float(self.int_time))
                self.change_int_time = False
            if self.change_avg_scans:
                self.avg_scans = self.next_avg_scans
                self.change_avg_scans = False
            temperature = self.camera.get_attribute_value("Sensor Temperature Reading")
            self.sendTemperature.emit(temperature)
        return

    def set_roi_parameters(self,y0, height, binning=None):
        """
            Changes the worker's ROI parameters and notifies the running loop that new parameters are available
            input:
                - y0 (int): index of the first sensor row to read
                - height (int): number of sensor rows covered by the region
                - binning (int, default None): number of rows summed on chip. None means sum the whole
                  region into a single row (the high signal-to-noise mode used for measurements).
                  Pass 1 to keep every row separate (the 2D mode used for alignment).
            output:
                - dict: the region of interest actually applied
        """
        y0 = int(np.clip(y0, 0, max(self.sensor_height - 1, 0)))
        height = int(np.clip(height, 1, self.sensor_height - y0))
        binning = height if binning is None else int(np.clip(binning, 1, height))
        # PICam requires the region height to be an exact multiple of the binning factor
        height = max((height // binning) * binning, binning)
        self.roi = {"x": 0, "width": 1024, "x_binning": 1,
                   "y": y0, "height": height, "y_binning": binning}
        self.roi_y0, self.roi_height, self.roi_binning = y0, height, binning
        self.new_roi=True
        return self.roi

    def set_roi(self):
        """
            Sets the vertical region of the sensor that is read out, and how many of its rows are
            summed on chip. Uses internally stored ROI dictionnary found in self.roi
            input:
        """
        self.camera.set_attribute_value("ROIs", [self.roi])
        self.new_roi=False
        logger.info('%s Pixis ROI updated'%(datetime.datetime.now()))

    def set_new_integration_time(self, int_time):
        """
            Sets a new integration time and flags the worker that it needs to be updated
            input:
                - int_time (float): New integration time in ms
        """
        self.int_time=int_time
        self.change_int_time = True
    def set_new_avg_scan(self,avg_scan):
        """
            Sets the number of average scans to be performed on each acquisition and flags the worker it needs to be updated.
            input:
                - avg_scan (int): Number of images to average
        """
        self.next_avg_scans = avg_scan
        self.change_avg_scans = True

    def close(self):
        """
            Shutdown routine for the Pixis Worker and Pixis
        """
        if self.camera is not None:
            self.camera.close()