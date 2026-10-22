# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 14:34:11 2025
@author: David Tiede
"""

import sys
import time
import re
import math
from collections import defaultdict
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial as P
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QApplication
import pyqtgraph as pg
from functools import partial
import pyqtgraph as pg
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from GUI.LUT_Calib_plot import LUT_Calib_plot
from GUI.VerticalCalibPlot import VerticalCalibPlot 
from GUI.SpectralCalibPlot import SpectralCalibDataPlot, SpectralCalibFitPlot
from GUI.ChirpCalibrationPlot import ChirpCalibrationPlot, ChirpSelectionPlot, ChirpFitPlot
from GUI.DelayCalibrationPlot import DelayCalibrationPlot, DelaySelectionPlot, DelayFitPlot
from GUI.MeasurementPlot import LOmeasurementPlot, MDCSmeasurementPlot, MDCSmeasurementFourierPlot
from GUI.LUT_Calib_plot import LUT_Calib_plot, LUT_Calib_intensity_plot
from GUI.SLMDisplay import SLMDisplay
from GUI.CameraDisplay import CameraDisplay
from GUI.AcquisitionSettings import AcquisitionSettings
from DataHandling.DataHandling import DataHandling
from measurements.MeasurementClasses import AcquireMeasurement,RunMeasurement,BackgroundMeasurement, ViewMeasurement
from measurements.MDCSClasses import AcquireLO, BoxcarGeometry
from measurements.CalibrationClasses import VerticalBeamCalibrationMeasurement, SpectralBeamCalibrationMeasurement, FitSpectralBeamCalibration, AcquireBackground, ChirpCalibrationMeasurement, FitTemporalBeamCalibration, DelayCalibrationMeasurement
from measurements.Calibration_Classes import Measure_LUT_PhasetoGreyscale,Generate_LUT_PhasetoGreyscale
from measurements.TGFROGClasses import TGFROGMeasurement, TGFROGRetrievalWorker
from GUI.PulseCharacterization import PulseCharacterization
from compute.beams import Beam
from samples.drivers.exemple_image_generation import beam_image_gen
from drivers.Instruments import load_instruments
from GUI.BeamExplorer import BeamExplorer
import logging
import datetime
from measurements.Calibration_Classes import Measure_LUT_PhasetoGreyscale,Generate_LUT_PhasetoGreyscale
import h5py
import os
import tkinter as tk
from tkinter import filedialog

logger = logging.getLogger(__name__)
class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainInterface, self).__init__()
        self.project_folder = Path(__file__).parent.resolve()
        uic.loadUi(Path(self.project_folder,r'GUI/main_GUI.ui'), self)
        logging.basicConfig(filename='main.log', level=logging.INFO)
        logger.info('%s Started log'%datetime.datetime.now())
        # fancy name
        self.setWindowTitle('COLBERTo')

        """ main_GUI.ui does not set tab overflow behaviour, so once enough tabs are added
        (11 as of this branch) neighbouring labels overlap instead of scrolling or eliding --
        seen between "LUT Calibration" and "Spatial Calibration". """
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.setElideMode(QtCore.Qt.ElideRight)

        self.devices, self.spectrometers = load_instruments()

        # find items to complement in GUI
        self.parameter_tree = self.findChild(QtWidgets.QTreeWidget, 'parameters_treeWidget')
        self.spectro_tab = self.findChild(QtWidgets.QWidget, 'spectro_tab')
        self.parameter_tab = self.findChild(QtWidgets.QWidget, 'parameter_tab')
        self.acquire_button = self.findChild(QtWidgets.QPushButton, 'acquire_pushButton')
        self.view_button = self.findChild(QtWidgets.QPushButton, 'view_pushButton')
        self.run_button = self.findChild(QtWidgets.QPushButton, 'run_pushButton')
        self.stop_button = self.findChild(QtWidgets.QPushButton, 'stop_pushButton')
        self.save_folder_button = self.findChild(QtWidgets.QPushButton, 'folder_pushButton')
        self.save_button = self.findChild(QtWidgets.QPushButton, 'save_pushButton')
        self.comments_edit = self.findChild(QtWidgets.QTextEdit, 'comments_textEdit')
        self.filename_edit = self.findChild(QtWidgets.QLineEdit, 'filename_lineEdit')
        self.progress_bar = self.findChild(QtWidgets.QProgressBar, 'progressBar')
        self.bg_button = self.findChild(QtWidgets.QPushButton, 'Acquire_bg_pushButton')
        self.bg_check_box = self.findChild(QtWidgets.QCheckBox, 'bg_checkBox')
        self.bg_file_indicator = self.findChild(QtWidgets.QLineEdit, 'bg_file_lineEdit')
        self.bg_scans_box = self.findChild(QtWidgets.QSpinBox, 'bg_scans_spinBox')
        self.bg_select_box = self.findChild(QtWidgets.QPushButton, 'select_bg_pushButton')
        self.grating_period_edit=self.findChild(QtWidgets.QSpinBox,'grating_period_spin_box')
        self.show_beam_explorer_pushbutton=self.findChild(QtWidgets.QPushButton,'show_beam_explorer_button')
        self.save_calibration_pushbutton = self.findChild(QtWidgets.QPushButton,'save_calibration_button')
        self.load_calibration_pushbutton = self.findChild(QtWidgets.QPushButton,'load_calibration_button')
        # Spatial calibration tab
        ## Vertical calibration tab
        self.spatial_calib_demo_mode_checkbox=self.findChild(QtWidgets.QCheckBox, 'spatial_calib_demo_mode_checkbox')
        self.spatial_calibration_tab= self.findChild(QtWidgets.QWidget, 'spatial_tab')
        self.vertical_calibration_box=self.findChild(QtWidgets.QGroupBox,'vertical_calibration_groupbox')
        self.vertical_calibration_plot_layout=self.findChild(pg.PlotWidget,'vertical_calib_plot_layout')
        self.vertical_calibration_runButton = self.findChild(QtWidgets.QPushButton, 'measure_vertical_calibration')
        self.assign_beams_vertical_delimiters_button= self.findChild(QtWidgets.QPushButton, 'assign_beams_button')
        self.beam_vertical_delimiters_table= self.findChild(QtWidgets.QTableWidget, 'beam_vertical_delimiters_table')
        self.row_increment=self.findChild(QtWidgets.QSpinBox,'row_increment_spin_box')
        ## Spectral calibration tab
        self.column_increment_spinbox=self.findChild(QtWidgets.QSpinBox,'column_increment_spin_box')
        self.column_width_spinbox=self.findChild(QtWidgets.QSpinBox,'column_width_spin_box')
        self.spectral_calibration_runButton = self.findChild(QtWidgets.QPushButton, 'measure_spectral_calibration')
        self.spectral_calibration_image_layout=self.findChild(pg.GraphicsLayoutWidget,'spectral_calib_plot_layout')
        self.shortest_fitting_wave_spin_box=self.findChild(QtWidgets.QSpinBox,'shortest_fitting_wave_spin_box')
        self.longest_fitting_wave_spin_box=self.findChild(QtWidgets.QSpinBox,'longest_fitting_wave_spin_box')
        self.spectral_fit_polynomial_order_spinbox=self.findChild(QtWidgets.QSpinBox,'polynomial_order_spin_box')
        self.fit_spectral_calibration_runButton = self.findChild(QtWidgets.QPushButton, 'fit_spectral_calibration_button')
        self.spectral_calibration_fit_plot_layout=self.findChild(pg.PlotWidget,'spectral_calib_fit_plot_layout')
        self.spectral_calibration_fit_residual_plot_layout=self.findChild(pg.PlotWidget,'spectral_calib_fit_residual_plot_layout')
        self.assign_spectral_calibration_button = self.findChild(QtWidgets.QPushButton, 'assign_spectral_calibration_button')
        self.kinetic_lineEdit = self.findChild(QtWidgets.QLineEdit, 'kinetic_lineEdit')
        self.kinetic_run_button = self.findChild(QtWidgets.QPushButton, 'kinetic_run_pushButton')
        self.SpecCalib_min_wavelength = self.findChild(QtWidgets.QSpinBox, 'SpecCalib_Wave_minimum_value')
        self.SpecCalib_max_wavelength = self.findChild(QtWidgets.QSpinBox, 'SpecCalib_Wave_maximum_value')                

        
        ## Chirp calibration tab
        self.chirp_calib_demo_mode_checkbox=self.findChild(QtWidgets.QCheckBox, 'Chirp_calib_demo_mode_checkbox')
        self.beam_name_box = self.findChild(QtWidgets.QComboBox,'Beam_name_box')
        self.compression_carrier_wavelength_Qline = self.findChild(QtWidgets.QLineEdit, 'Compression_carrier_wavelength')
        self.chirp_step_Qline = self.findChild(QtWidgets.QLineEdit, 'Chirp_step')
        self.chirp_max_Qline = self.findChild(QtWidgets.QLineEdit, 'Chirp_max')
        self.chirp_min_Qline = self.findChild(QtWidgets.QLineEdit, 'Chirp_min')
        self.background_chirp_data_runbutton = self.findChild(QtWidgets.QPushButton, 'Background_data_temp_calibration')
        self.acquire_chirp_data_runButton = self.findChild(QtWidgets.QPushButton, 'Acquire_data_temp_calibration')
        self.chirp_calibration_image_layout=self.findChild(pg.GraphicsLayoutWidget,'Chirp_plot_layout')
        
        self.chirp_SNR_threshold_value = self.findChild(QtWidgets.QDoubleSpinBox,'SNR_threshold_value')
        self.chirp_apply_SNR_button = self.findChild(QtWidgets.QPushButton, 'SNR_temporal_calibration_button')
        self.chirp_min_wavelength_value = self.findChild(QtWidgets.QSpinBox, 'Wavelength_minimum_value')
        self.chirp_max_wavelength_value = self.findChild(QtWidgets.QSpinBox, 'Wavelength_maximum_value')
        self.chirp_polynomial_order_value = self.findChild(QtWidgets.QSpinBox, 'Polynomial_order_value')
        self.chirp_fit_calibration_button = self.findChild(QtWidgets.QPushButton, 'fit_temporal_calibration_button')
        self.chirp_coeff = self.findChild(QtWidgets.QTextEdit, 'Chirp_fitted_coefficients')
        self.chirp_assign_calibration_button = self.findChild(QtWidgets.QPushButton, 'assign_temporal_calibration_button')
        self.chirp_remove_calibration_button = self.findChild(QtWidgets.QPushButton, 'remove_temporal_calibration_button')
        self.chirp_selection_layout = self.findChild(pg.GraphicsLayoutWidget, 'Chirp_selection')
        self.chirp_fit_layout = self.findChild(pg.PlotWidget, 'Chirp_fit')

        ## Delay calibration tab
        self.delay_backgroud_button = self.findChild(QtWidgets.QPushButton, 'Delay_background_button')
        self.delay_acquire_button = self.findChild(QtWidgets.QPushButton, 'Delay_acquire_button')
        self.delay_demo_mode_checkbox = self.findChild(QtWidgets.QCheckBox, 'Delay_demo_mode_checkbox')
        self.delay_reference_beam_name_box = self.findChild(QtWidgets.QComboBox,'Delay_reference_beam_name_box')
        self.delay_second_beam_name_box = self.findChild(QtWidgets.QComboBox,'Delay_second_beam_name_box')
        self.delay_carrier_wavelength_value = self.findChild(QtWidgets.QLineEdit, 'Delay_carrier_wavelength_value')
        self.delay_min_group_delay_value = self.findChild(QtWidgets.QLineEdit, 'Delay_min_group_delay_value')
        self.delay_max_group_delay_value = self.findChild(QtWidgets.QLineEdit, 'Delay_max_group_delay_value')
        self.delay_step_group_delay_value = self.findChild(QtWidgets.QLineEdit, 'Delay_step_group_delay_value')
        self.delay_SNR_threshold_value = self.findChild(QtWidgets.QDoubleSpinBox,'Delay_SNR_threshold_value')
        self.delay_apply_SNR_treshold_button = self.findChild(QtWidgets.QPushButton, 'Delay_apply_SNR_threshold_button')
        self.delay_min_wavelength_bandwidth_value = self.findChild(QtWidgets.QSpinBox, 'Delay_min_wavelength_bandwidth_value')
        self.delay_max_wavelength_bandwidth_value = self.findChild(QtWidgets.QSpinBox, 'Delay_max_wavelength_bandwidth_value')
        self.delay_fit_delay_button = self.findChild(QtWidgets.QPushButton, 'Delay_fit_delay_button')
        self.delay_apply_delay_button = self.findChild(QtWidgets.QPushButton, 'Delay_apply_delay_button')
        self.delay_remove_delay_button = self.findChild(QtWidgets.QPushButton, 'Delay_remove_delay_button')
        self.delay_scan_plot = self.findChild(pg.GraphicsLayoutWidget, 'Delay_scan_plot')
        self.delay_fit_plot = self.findChild(pg.PlotWidget, 'Delay_fit_plot')

        ## Measurement tab
        self.MDCS_demo_mode_checkbox = self.findChild(QtWidgets.QCheckBox, 'Measurement_demo_mode_checkbox')
        self.MDCS_phase_cycling_checkbox = self.findChild(QtWidgets.QCheckBox, 'Measurement_phase_cycling_checkbox')
        self.MDCS_measurement_type_box = self.findChild(QtWidgets.QComboBox, 'Measurement_type_box')
        self.MDCS_TLO_delay_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_TLO_delay_value')
        self.MDCS_scanned_delay_min_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_scanned_delay_min_value')
        self.MDCS_scanned_delay_max_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_scanned_delay_max_value')
        self.MDCS_scanned_delay_step_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_scanned_delay_step_value')
        self.MDCS_secondary_delay_min_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_secondary_delay_min_value')
        self.MDCS_secondary_delay_max_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_secondary_delay_max_value')
        self.MDCS_secondary_delay_step_value = self.findChild(QtWidgets.QLineEdit, 'Measurement_secondary_delay_step_value')
        self.MDCS_getLO_button = self.findChild(QtWidgets.QPushButton, 'Measurement_getLO_button')
        self.MDCS_acquire_button = self.findChild(QtWidgets.QPushButton, 'Measurement_acquire_button')
        self.MDCS_LO_plot = self.findChild(pg.PlotWidget, 'Local_oscillator_plot')
        self.MDCS_2D_plot = self.findChild(pg.GraphicsLayoutWidget, 'Measurement_plot')
        self.MDCS_Fourier_real_plot = self.findChild(pg.GraphicsLayoutWidget, 'Measurement_result_real_plot')
        self.MDCS_Fourier_imag_plot = self.findChild(pg.GraphicsLayoutWidget, 'Measurement_result_imaginary_plot')

        # LUT Calibration - Utilities
        self.LUT_calibration_box = self.findChild(QtWidgets.QGroupBox, 'LUT_calibration')
        self.LUT_grating_period = self.findChild(QtWidgets.QDoubleSpinBox, 'LUT_grating_period_value')
        self.LUT_calib_central_wavelength = self.findChild(QtWidgets.QDoubleSpinBox, 'LUT_calib_central_wavelength_value')
        self.LUT_calib_0 = self.findChild(QtWidgets.QSpinBox, 'LUT_calib_0_value')
        self.LUT_calib_2pi = self.findChild(QtWidgets.QSpinBox, 'LUT_calib_2pi_value')
        self.LUT_calib_plot_layout = self.findChild(pg.PlotWidget, 'LUT_calib_plot_layout')
        self.LUT_calib_plot_layout_2 = self.findChild(pg.PlotWidget, 'LUT_calib_plot_layout_2')
        self.LUT_measure_spectrum_button = self.findChild(QtWidgets.QPushButton, 'LUT_measure_spectrum_button')
        self.LUT_generate_LUT_file_button = self.findChild(QtWidgets.QPushButton, 'LUT_generate_LUT_file_button')
        self.LUT_clear_graph_button = self.findChild(QtWidgets.QPushButton, 'LUT_clear_graph_button')
        self.LUT_load_LUT_file_button = self.findChild(QtWidgets.QPushButton, 'LUT_load_LUT_file_button')
        #SLM Related
        self.slm_display=self.findChild(pg.GraphicsLayoutWidget,'slm_display')
        

        #Cryostat
        if 'cryostat' in self.devices:

            if hasattr(self, 'CryostatTab'):
                self.CryostatTab.set_driver(self.devices['cryostat'])

        # Spectrometer Selection
        self.spectrometer_select = self.findChild(QtWidgets.QComboBox, 'spec_selection_comboBox')

        if self.spectrometer_select is not None:
            logger.info(f"Available spectrometers: {list(self.spectrometers.keys())}")

            self.spectrometer_select.addItems(self.spectrometers.keys())

            # Determine default spectrometer
            default_name = self.devices.get('spectrometer_name', 'Ocean')  # fallback to 'Ocean' or 'Demo'
            if default_name not in self.spectrometers:
                default_name = next(iter(self.spectrometers))  # pick first available

            # Set default spectrometer in both dropdown and device dict
            self.spectrometer_select.setCurrentText(default_name)
            self.active_spectrometer = self.spectrometers[default_name]
            self.devices['spectrometer'] = self.active_spectrometer
            self.spec_length = getattr(self.active_spectrometer, 'spec_length', 2048)

            # Connect handler for when selection changes
            self.spectrometer_select.currentTextChanged.connect(self.on_spectrometer_changed)

        self.active_spectrometer = self.devices['spectrometer']
        logger.info(f"Available Devices: {list(self.devices.keys())}")

        # initial parameter values, retrieved from devices
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for device in self.devices.keys():
            self.parameter_dic[device] = self.devices[device].parameter_display_dict

        # build flat parameter dict (Not building the UI only creating the DATA structure)
        self.parameter = {}
        for device in self.parameter_dic:
            for param in self.parameter_dic[device]:
                self.parameter[param] = self.parameter_dic[device][param]['val']

        # create parameter array for easy access
        # self.create_parameter_array()

        # add items to GUI
        self.SpectrometerPlot = SpectrometerPlot()
        self.ParameterPlot = ParameterPlot(self.parameter_dic)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.ParameterPlot)
        self.parameter_tab.setLayout(vbox)

        self.VerticalCalibPlot= VerticalCalibPlot(self.vertical_calibration_plot_layout)
        self.SpectralCalibDataPlot= SpectralCalibDataPlot(self.spectral_calibration_image_layout)
        self.SpectralCalibrationFitPlot= SpectralCalibFitPlot(self.spectral_calibration_fit_plot_layout,self.spectral_calibration_fit_residual_plot_layout)
        self.ChirpCalibrationPlot= ChirpCalibrationPlot(self.chirp_calibration_image_layout)
        self.ChirpSelectionPlot = ChirpSelectionPlot(self.chirp_selection_layout)
        self.ChirpFitplot = ChirpFitPlot(self.chirp_fit_layout)
        self.DelayCalibrationPlot = DelayCalibrationPlot(self.delay_scan_plot)
        self.DelayFitPlot = DelayFitPlot(self.delay_fit_plot)
        self.LOspectrumPlot = LOmeasurementPlot(self.MDCS_LO_plot)
        self.MDCSplot = MDCSmeasurementPlot(self.MDCS_2D_plot)
        self.MDCSFourierRealPlot = MDCSmeasurementFourierPlot(self.MDCS_Fourier_real_plot)
        self.MDCSFourierImagPlot = MDCSmeasurementFourierPlot(self.MDCS_Fourier_imag_plot)
        self.LUT_Calib_plot = LUT_Calib_plot(self.LUT_calib_plot_layout)
        self.LUT_Calib_plot_2 = LUT_Calib_intensity_plot(self.LUT_calib_plot_layout_2)
        self.slm_display_plot= SLMDisplay(self.slm_display)

        """ The spectro tab is composed here rather than in main_GUI.ui: the .ui file is edited by
        several people in Qt Designer and merges badly, so it leaves spectro_tab empty and everything
        is assembled in code. Top row is the acquisition settings beside the live camera view, bottom
        row is the spectrum. Splitters rather than a fixed grid, so the spectrum can be dragged to
        take the whole height once alignment is done. """
        self.CameraDisplay = CameraDisplay()
        """ Changing the readout region changes the scale of the counts by the number of rows summed,
        so a curve taken under the previous region would dominate the axes and make the new one read
        as flat at zero. """
        self.CameraDisplay.roi_applied.connect(self.readout_region_changed)
        self.AcquisitionSettings = AcquisitionSettings()
        self.AcquisitionSettings.is_busy = lambda: self.measurement_busy
        self.AcquisitionSettings.parameter_changed = self.spectrometer_parameter_changed

        """ The settings panel is laid out to fit without scrolling, so it goes in directly. It is
        given the width its controls need rather than a fixed fraction: clipped labels made the first
        version unreadable. """
        top_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        top_splitter.addWidget(self.AcquisitionSettings)
        top_splitter.addWidget(self.CameraDisplay)
        """ Equal halves rather than pixel sizes: the sizes are treated as proportions, so the split
        holds on any screen instead of depending on the font metrics of one machine. """
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)
        top_splitter.setSizes([1000, 1000])

        spectro_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        spectro_splitter.addWidget(top_splitter)
        spectro_splitter.addWidget(self.SpectrometerPlot)
        """ 40/60 still wasn't enough vertical room for the 1D spectrum on a laptop screen;
        give it roughly two thirds instead. """
        spectro_splitter.setStretchFactor(0, 1)
        spectro_splitter.setStretchFactor(1, 2)
        spectro_splitter.setSizes([600, 1400])

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(spectro_splitter)
        self.spectro_tab.setLayout(vbox)

        """ Built and added the same way as the spectro tab above, rather than as a placeholder
        in main_GUI.ui, for the same reason: the .ui file merges badly between contributors. """
        self.PulseCharacterization = PulseCharacterization()
        self.tabWidget.addTab(self.PulseCharacterization, 'Pulse characterization')

        """ Second tab holding nothing but the spectrum: in the lab the plot is read from across the
        room, where the controls only get in the way. Two plot instances fed the same data, rather
        than moving one widget between tabs. """
        self.SpectrometerPlotFull = SpectrometerPlot()
        self.tabWidget.insertTab(1, self.SpectrometerPlotFull, 'Spectrum')
        self.spectrum_plots = [self.SpectrometerPlot, self.SpectrometerPlotFull]

        self.connect_camera_display()
        self.connect_acquisition_settings()

        """ This initializes the parameter tree. It is constructed based on the device dict,
        that includes parameter information of each device """
        self.parameter_tree.setColumnCount(2)
        self.parameter_tree.setHeaderLabels(["Name", "Value"])
        self.parameter_widgets = {}
        self.readonly_parameter = []
        self.writeonly_parameter = []
        for device in self.parameter_dic.keys():
            item = QtWidgets.QTreeWidgetItem([device.capitalize()])
            self.parameter_tree.addTopLevelItem(item)
            for param in self.parameter_dic[device].keys():
                self._build_parameter_tree_item(item, device, param)

        # start DataHandling
        # self.spec_length = self.devices['spectrometer'].get_num_pixel()
        self.DataHandling = DataHandling(self.parameter, self.spec_length)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        for plot in self.spectrum_plots:
            self.DataHandling.sendSpectrum.connect(plot.set_data)
            self.DataHandling.sendMaximum.connect(plot.update_datareader)

        #start Beam explorer
        self.beam_explorer = BeamExplorer(self.DataHandling.get_beams())
        self.show_beam_explorer()

        # start Updater to update device read parameters
        self.Updater = UpdateWorker(self.devices, self.readonly_parameter)
        self.Updater.new_parameter.connect(self.update_read_parameter)
        self.Updater.start()

        # set variables
        self.measurement_busy = False
        self.save_folder_path = r'C:/data/Colbert'
        #a default data folder is always required and it would be good to keep it seperated from the code.
        #can everyone simply create a C:/Data/test' path on their device? # Not sure how to handle different OS here.
        self.filename = r'C:/Data/test'
        self.power_calib_array = []

        # set connect events
        self.acquire_button.clicked.connect(self.acquire_measurement)
        self.view_button.clicked.connect(self.view_measurement)
        self.run_button.clicked.connect(self.run_measurement)
        self.stop_button.clicked.connect(self.stop_measurement)
        self.filename_edit.editingFinished.connect(self.change_filename)
        self.save_button.clicked.connect(self.save_data)
        self.save_folder_button.clicked.connect(self.change_folder)
        self.bg_button.clicked.connect(self.background_measurement)
        self.bg_select_box.clicked.connect(self.load_bg)
        self.bg_check_box.stateChanged.connect(self.update_check_bg)
        self.ParameterPlot.send_idx_change.connect(self.DataHandling.change_send_idx)
        self.ParameterPlot.send_parameter_filename.connect(self.DataHandling.save_parameter)
        # Vertical calibration connect events
        self.vertical_calibration_runButton.clicked.connect(self.verticalBeamCalibrationMeasurement)
        self.beam_vertical_delimiters_table.cellChanged.connect(self.verticalBeamDelimitersChanged)
        self.assign_beams_vertical_delimiters_button.clicked.connect(self.assign_vertical_beam_calibration)
        # Spectral calibration connect events
        self.spectral_calibration_runButton.clicked.connect(self.spectralBeamCalibrationMeasurement)
        self.shortest_fitting_wave_spin_box.valueChanged.connect(self.update_spectra_calibration_boundaries)
        self.longest_fitting_wave_spin_box.valueChanged.connect(self.update_spectra_calibration_boundaries)
        self.fit_spectral_calibration_runButton.clicked.connect(self.fit_spectral_calibration)
        self.assign_spectral_calibration_button.clicked.connect(self.assign_spectral_calibration)
        # LUT Calibration Measurement Connect Events
        self.LUT_measure_spectrum_button.clicked.connect(self.Measure_LUT_PhasetoGreyscale)  # measure spectrum
        self.LUT_generate_LUT_file_button.clicked.connect(self.Generate_LUT_PhasetoGreyscale)  # use spectrum data to generate LUT file
        self.LUT_clear_graph_button.clicked.connect(self.LUT_Calib_plot_2.clear_all)
        self.LUT_load_LUT_file_button.clicked.connect(self.Load_LUT_PhasetoGrayscale)
        # Chirp calibration connect events
        self.background_chirp_data_runbutton.clicked.connect(self.BackgroundMeasurement)
        self.acquire_chirp_data_runButton.clicked.connect(self.chirpCalibrationMeasurement)
        self.chirp_SNR_threshold_value.valueChanged.connect(self.update_temporal_calibration_boundaries)
        self.chirp_min_wavelength_value.valueChanged.connect(self.update_temporal_calibration_boundaries)
        self.chirp_max_wavelength_value.valueChanged.connect(self.update_temporal_calibration_boundaries)
        self.chirp_apply_SNR_button.clicked.connect(self.applySNRthreshold)
        self.chirp_fit_calibration_button.clicked.connect(self.fitChirpMeasurement)
        self.chirp_assign_calibration_button.clicked.connect(lambda: self.assignTemporalCalibration(1))
        self.chirp_remove_calibration_button.clicked.connect(lambda: self.assignTemporalCalibration(-1))
        # Delay calibration connect events
        self.delay_backgroud_button.clicked.connect(self.BackgroundMeasurement)
        self.delay_acquire_button.clicked.connect(self.delayAcquireMeasurement)
        self.delay_SNR_threshold_value.valueChanged.connect(self.delayApplySNRThreshold)
        self.delay_apply_SNR_treshold_button.clicked.connect(self.delayApplySNRThreshold)
        self.delay_min_wavelength_bandwidth_value.valueChanged.connect(self.delayApplySNRThreshold)
        self.delay_max_wavelength_bandwidth_value.valueChanged.connect(self.delayApplySNRThreshold)
        self.delay_fit_delay_button.clicked.connect(self.delayFitMeaserement)
        self.delay_apply_delay_button.clicked.connect(lambda: self.assignDelayCalibration(1))
        self.delay_remove_delay_button.clicked.connect(lambda: self.assignDelayCalibration(-1))

        self.PulseCharacterization.start_button.clicked.connect(self.tgfrogAcquireMeasurement)
        self.PulseCharacterization.retrieve_button.clicked.connect(self.tgfrogRetrieveMeasurement)
        # Measurement tab connect events
        self.MDCS_getLO_button.clicked.connect(self.getLOSpectrum)
        self.MDCS_acquire_button.clicked.connect(self.MDCSacquireMeasurement)
        # SLM display connections
        self.devices['SLM'].slm_worker.imageSLM.connect(self.slm_display_plot.set_data)
        test_image=beam_image_gen()
        # Beam update connection
        self.DataHandling.sendBeams.connect(self.beam_explorer.receive_beams)
        self.DataHandling.sendBeams.connect(self.update_beam_name_list)
        self.DataHandling.sendBeams.connect(self.PulseCharacterization.update_beam_names)
        #Beam Explorer related
        self.beam_explorer.beams_changed.connect(self.DataHandling.set_multiple_beams)
        self.beam_explorer.phase_image.connect(self.devices['SLM'].write_image)
        self.show_beam_explorer_pushbutton.clicked.connect(self.show_beam_explorer)
        self.devices['SLM'].write_image(test_image)
        # Save/load calibration
        self.save_calibration_pushbutton.clicked.connect(lambda: self.save_calibration(filename_prefix="Filename", use_prompt=True, save_dir=None))
        self.load_calibration_pushbutton.clicked.connect(self.load_calibration)
        # run some functions once to define default values
        self.change_filename()

        # show GUI, to be executed at the end of init.
        self.show()

    ##### General functions #####
    def on_spectrometer_changed(self, new_name):
        if new_name not in self.spectrometers:
            logger.warning(f"Unknown spectrometer selected: {new_name}")
            return

        # Switch spectrometer object
        self.active_spectrometer_name = new_name
        self.active_spectrometer = self.spectrometers[new_name]
        self.devices['spectrometer'] = self.active_spectrometer

        # Update spectral length
        self.spec_length = getattr(self.active_spectrometer, 'spec_length', 2048)
        self.DataHandling.update_spec_length(self.spec_length)

        # Rebuild parameter dictionary safely
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for name, dev in self.devices.items():
            if hasattr(dev, 'parameter_display_dict'):
                self.parameter_dic[name] = dev.parameter_display_dict

        # ---- CLEAR OLD WIDGET REFERENCES (CRITICAL) ----
        self.parameter_widgets.clear()
        self.readonly_parameter.clear()
        self.writeonly_parameter.clear()

        # Rebuild parameter tree UI (existing code)
        self.create_parameter_array()

        self.parameter = {}
        for device in self.parameter_dic:
            for param in self.parameter_dic[device]:
                self.parameter[param] = self.parameter_dic[device][param]['val']
        self.DataHandling.change_spectrometer(self.spec_length)

        self.connect_camera_display()
        self.connect_acquisition_settings()

        logger.info(
            f"Switched to spectrometer: {new_name} "
            f"(spec_length={self.spec_length})"
        )

    def connect_camera_display(self):
        '''
            Points the Camera tab at the active spectrometer.
            Cameras with a 2D sensor expose their raw frames through a worker signal; those frames are
            routed straight to the view so alignment can be checked without going through DataHandling,
            which only carries the 1D spectra used for measurements. Spectrometers without a
            configurable readout region (checked via set_binned_roi, the same test CameraDisplay
            uses to enable its controls) simply leave the tab disabled: their worker's sendSpectrum
            signal is not guaranteed to share Pixis's (image, int_time) signature, and CameraDisplay
            is only meaningful for a 2D sensor in the first place.
        '''
        previous = getattr(self, '_camera_display_source', None)
        if previous is not None:
            try:
                previous.sendSpectrum.disconnect(self.CameraDisplay.set_data)
            except (TypeError, RuntimeError):
                pass  # already disconnected or worker gone
        self._camera_display_source = None

        spectrometer = self.devices.get('spectrometer')
        self.CameraDisplay.set_spectrometer(spectrometer)

        worker = getattr(spectrometer, 'worker', None)
        if worker is not None and hasattr(spectrometer, 'set_binned_roi') and hasattr(worker, 'sendSpectrum'):
            worker.sendSpectrum.connect(self.CameraDisplay.set_data)
            self._camera_display_source = worker
            logger.info('%s Camera view connected to %s'
                        % (datetime.datetime.now(), getattr(spectrometer, 'name', spectrometer)))

    def readout_region_changed(self, y0, height):
        '''
            Clears the spectrum plots after the camera readout region changed.
            input:
                - y0 (int): first sensor row now read
                - height (int): number of rows now covered
        '''
        for plot in self.spectrum_plots:
            plot.clear_plot()
        logger.info('%s Readout region changed to rows %d-%d, spectrum plots cleared'
                    % (datetime.datetime.now(), y0, y0 + height - 1))

    def spectrometer_parameter_changed(self, parameter, value):
        '''
            Called by the Acquisition panel after it has set a camera parameter on the driver.
            The tree row is read-only for the spectrometer, so nothing else would refresh it, and
            self.parameter is what gets recorded alongside the data: both have to follow.
            input:
                - parameter (str): parameter name
                - value (float): value that was applied
        '''
        self.parameter[parameter] = value
        widget = self.parameter_widgets.get(parameter)
        if widget is not None:
            widget.setValue(value)

    def connect_acquisition_settings(self):
        '''
            Points the Acquisition tab at the active spectrometer. Cameras without a configurable
            trigger leave the tab disabled, the same way the Camera tab handles sensors without a
            configurable readout region.
        '''
        spectrometer = self.devices.get('spectrometer')
        self.AcquisitionSettings.set_spectrometer(spectrometer)
        self.AcquisitionSettings.set_monochromator(self.devices.get('Monochrom'))
        if hasattr(spectrometer, 'set_acquisition_mode'):
            logger.info('%s Acquisition settings connected to %s'
                        % (datetime.datetime.now(), getattr(spectrometer, 'name', spectrometer)))


    def create_parameter_array(self):
        # initialization function to store all parameters in one array

        # ---- CLEAR EVERYTHING ONCE ----
        self.parameter_tree.clear()
        self.parameter = {}
        self.parameter_widgets = {}
        self.readonly_parameter = []
        self.writeonly_parameter = []

        # ---- FLATTEN PARAMETERS (if still needed elsewhere) ----
        for device in self.parameter_dic.keys():
            for param in self.parameter_dic[device].keys():
                self.parameter[param] = self.parameter_dic[device][param]['val']

        for device in self.parameter_dic.keys():
            item = QtWidgets.QTreeWidgetItem([device.capitalize()])
            self.parameter_tree.addTopLevelItem(item)

            for param in self.parameter_dic[device].keys():
                self._build_parameter_tree_item(item, device, param)

    def _build_parameter_tree_item(self, item, device, param):
        '''
            Builds one row of the parameter tree (name label + value spinbox) for a
            single device parameter and registers the resulting widget in
            self.parameter_widgets/readonly_parameter/writeonly_parameter.
            Cryostat parameters are always shown read-only here regardless of the
            driver's 'read' flag: control of the cryostat must go through the
            dedicated CryostatTab page. This tree only displays/logs its value.
        '''
        child = QtWidgets.QTreeWidgetItem()
        item.addChild(child)

        name_widget = QtWidgets.QLabel(param)
        spin = QtWidgets.QDoubleSpinBox()
        self.parameter_widgets[param] = spin

        param_info = self.parameter_dic[device][param]
        """ The spectrometer joins the cryostat in being read-only here: its settings are edited in
        the Acquisition panel of Spectrum View, beside the acquisition they affect, and this tree
        shows them so the whole hardware state can be read at a glance. The SLM and the other devices
        keep their editable rows. """
        force_read_only = device in ('cryostat', 'spectrometer')
        spin.setReadOnly(param_info['read'] or force_read_only)

        try:
            spin.setSuffix(param_info['unit'])
            spin.setMaximum(param_info['max'])
        except Exception:
            pass

        try:
            spin.setMinimum(param_info['min'])
        except Exception:
            pass

        if param_info['read']:
            self.readonly_parameter.append(param)
        elif force_read_only:
            spin.setValue(param_info['val'])
            self.readonly_parameter.append(param)
        else:
            spin.setValue(param_info['val'])
            spin.editingFinished.connect(partial(self.set_parameter, param))
            self.writeonly_parameter.append(param)

        self.parameter_tree.setItemWidget(child, 0, name_widget)
        self.parameter_tree.setItemWidget(child, 1, spin)



    def update_read_parameter(self, new_parameter):
        for param in new_parameter.keys():
            if param in self.parameter_widgets:
                try:
                    self.parameter_widgets[param].setValue(new_parameter[param])
                except TypeError:
                    # Si le paramètre est du texte (ex: "Stable"), on ignore l'erreur du spinbox
                    pass

        """ Record the hardware state alongside the data. The Updater only carries the read-only
        parameters, so it is merged over the settings held here to give the full picture. Nothing
        called DataHandling.update_parameter() before, which is why saved files carried no hardware
        settings at all. """
        recorded = dict(self.parameter)
        recorded.update(new_parameter)
        self.DataHandling.update_parameter(recorded)


    def change_parameter(self, parameter, value):
        # change parameter when called from another script
        self.parameter_widgets[parameter].setValue(value)
        self.set_parameter(parameter)

    def set_parameter(self, new_parameter):
        # set parameter when Spinbox is changed and send it to devices and DataHandling
        for device in self.devices.keys():
            if new_parameter in self.devices[device].parameter_dict.keys():
                # get parameter from widget
                value = self.parameter_widgets[new_parameter].value()
                self.devices[device].set_parameter(new_parameter, value)
                # change parameter in DataHandling
                self.parameter[new_parameter] = value

    def test(self):
        # test function to test anything
        logger.info('%s I am testing'%datetime.datetime.now())

    def set_progress(self, progress):
        # set progress bar and define whether a measurement is running. When progess ne 100, no new measurement starts
        self.progress_bar.setValue(int(progress))
        if progress == 100.:
            self.measurement_busy = False

    def change_folder(self):
        # select folder to save data
        self.save_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select data saving folder')
        logger.info('%s Data folder: %s'%(datetime.datetime.now(),str(self.save_folder_path)))
        self.change_filename()

    def change_filename(self):
        # change filename to string of LineEdit
        self.filename = str(self.save_folder_path) + "/" + str(self.filename_edit.text().strip('\n'))
        logger.info('%s filename changed to: %s'%(datetime.datetime.now(),str(self.filename)))

    def save_data(self):
        # save data
        self.DataHandling.save_data(self.filename, self.comments_edit.toPlainText())

    def load_bg(self):
        # open background file and set as background
        BackgroundFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        bg_path = BackgroundFile[0]

        ############  '''## Load datasets and attributes ##''' #############
        with h5py.File(bg_path, 'r') as hdf:
            ls = list(hdf.keys())
            print('List of Data Sets in this file: \n', ls)

            data = hdf.get('spectra')
            param_set = hdf.get('parameter')

            data_set = np.array([np.asarray(x, dtype=float).flatten() for x in data])
            param_set = np.array([np.asarray(x, dtype=float).flatten() for x in param_set])

            grf = hdf['parameter']
            params = grf.attrs['parameter_keys']

            grp = hdf['spectra']
            wave = grp.attrs['xaxis']

        bg = data_set
        """ Routed through use_background() so the length is checked against the active spectrometer
        and the background is marked as usable. Assigning the attribute directly left has_background
        false, and a file of the wrong length was accepted without a word. """
        if not self.DataHandling.use_background(bg):
            self.bg_file_indicator.setText('rejected: wrong length')
            return wave, bg

        # display measured spectra filepath
        idx = bg_path.rfind('/')
        self.bg_file_indicator.setText(bg_path[idx + 1:])

        return wave, bg

    def update_check_bg(self):
        self.DataHandling.correct_background = self.bg_check_box.isChecked()

    def change_kinetic_interval(self):
        # generate timing array for time resolved measurement
        try:
            self.kinetic_interval = []
            txt = self.kinetic_lineEdit.text()
            for s in re.split(' ', txt):
                if s == "o":
                    self.kinetic_interval.append('open')
                elif s == "c":
                    self.kinetic_interval.append('close')
                elif s == "":
                    pass
                    pass
                elif s[0] == "p":
                    numbers = re.split(":", s[1:])
                    probint = np.linspace(float(numbers[0]), float(numbers[2]), int(numbers[1]))
                    for i in range(len(probint)):
                        self.kinetic_interval.append('p'+str(probint[i]))
                else:
                    numbers = re.split(':', s)
                    self.kinetic_interval.append(np.linspace(float(numbers[0]), float(numbers[2]), int(numbers[1])))
            logger.info('%s Kinetic Interval: %s'%(datetime.datetime.now(),str(self.kinetic_interval)))
        except:
            logger.warning('%s Lecture of kinetic interval failed'%datetime.datetime.now())

    ##### Measurements #####

    def acquire_measurement(self):
        # take one spectrum with spectrometer
        if self.measurement_busy:
            """ take_spectrum() runs the blocking hardware readout, and this is the GUI thread: calling
            it here froze the whole interface for as long as the camera took to answer. Let the running
            measurement finish instead. """
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())
        else:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = AcquireMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.start()

    def view_measurement(self):
        # take one spectrum with spectrometer
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = ViewMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            for plot in self.spectrum_plots:
                self.measurement.sendClear.connect(plot.clear_plot)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())

    def run_measurement(self):
        # continuously taking spectra with spectrometer
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = RunMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())

    def background_measurement(self):
        # acquire background to subtract from spectra. May average over several spectra
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = BackgroundMeasurement(self.devices, self.parameter, self.bg_scans_box.value(),
                                                     self.filename, self.comments_edit.toPlainText())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            """ Without this the measured background was only ever stored as ordinary data: nothing
            assigned DataHandling.background except loading a file, so acquiring a background and
            ticking the correction box subtracted an uninitialised array. """
            self.measurement.sendSpectrum.connect(self.DataHandling.set_background)
            self.measurement.sendSave.connect(self.DataHandling.save_data)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())

    def verticalBeamCalibrationMeasurement(self):
        '''
             Sets up and starts a vertical Beam Calibration.
        ''' 
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement= VerticalBeamCalibrationMeasurement(self.devices,self.grating_period_edit.value(),self.row_increment.value(),demo=self.spatial_calib_demo_mode_checkbox.isChecked())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.send_intensities.connect(self.VerticalCalibPlot.set_data)
            self.measurement.send_vertical_calibration_data.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())
    
    def verticalBeamDelimitersChanged(self,row_index,col_index):
        '''
            Validates the vertical delimiter change and refreshes the vertical beam delimiters plot when they are changed in the table
            input:
                - row_index (int): the index of the row of the changed column
                - col_index (int): the index of the row of the changed column
        '''
        regions={}
        table=self.beam_vertical_delimiters_table
        if not col_index==0: #In case didn,t change the label of the beam
            try:
                added_item=int(table.item(row_index,col_index).text())# Check for integer
                if any([added_item<0,added_item>self.devices['SLM'].get_height()]):# Check for proper bounds
                    raise ValueError
                for row in range(table.rowCount()):
                    top_index=int(table.item(row,1).text()) if table.item(row,1) is not None else None
                    bottom_index=int(table.item(row,2).text()) if table.item(row,2) is not None else None
                    label=table.item(row,0).text()
                    regions[label]=[top_index,bottom_index]
                self.VerticalCalibPlot.draw_regions(regions)
            except ValueError:
                table.setItem(row_index,col_index,None)

    def assign_vertical_beam_calibration(self):
        '''
            Saves the current vertical beam calibration to the DataHandling
        '''
        table=self.beam_vertical_delimiters_table
        for row in range(table.rowCount()):
            top_index=int(table.item(row,1).text()) if table.item(row,1) is not None else None
            bottom_index=int(table.item(row,2).text()) if table.item(row,2) is not None else None
            label=table.item(row,0).text() if table.item(row,0).text() is not None else None
            if all([label is not None, bottom_index is not None, top_index is not None]):
                beam = Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())
                beam.set_beamVerticalDelimiters([top_index,bottom_index])
                beam.set_gratingPeriod(self.grating_period_edit.value())
                self.DataHandling.set_beam((label,beam))
                
    def update_beam_name_list(self, beamDict):
        old = self.beam_name_box.currentText()
        self.beam_name_box.clear()
        self.beam_name_box.addItems(beamDict)
        if old in beamDict:
            self.beam_name_box.setCurrentText(old)

        old = self.delay_reference_beam_name_box.currentText()
        self.delay_reference_beam_name_box.clear()
        self.delay_reference_beam_name_box.addItems(beamDict)
        if old in beamDict:
            self.delay_reference_beam_name_box.setCurrentText(old)

        old = self.delay_second_beam_name_box.currentText()
        self.delay_second_beam_name_box.clear()
        self.delay_second_beam_name_box.addItems(beamDict)
        if old in beamDict:
            self.delay_second_beam_name_box.setCurrentText(old)

    def BackgroundMeasurement(self):
        if not self.measurement_busy:
            self.measurement_busy = True
            self.background = AcquireBackground(self.devices)
            self.background.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.background.send_background.connect(self.DataHandling.add_calibration)
            self.background.sendProgress.connect(self.set_progress)
            self.background.start()
    
    def chirpCalibrationMeasurement(self):
        '''
            Sets up and starts a temporal Beam Calibration.
        ''' 
        if not self.measurement_busy:
            self.measurement_busy = True
            if self.beam_name_box.currentText() in self.DataHandling.get_beams():
                beam = self.DataHandling.get_beams()[self.beam_name_box.currentText()]
            else:
                beam = Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())
            self.DataHandling.clear_data() 
            if hasattr(self, 'background'):
                chirpbackground = self.DataHandling.calibration['background_data']
                background = chirpbackground['spec']
            else:
                background = 0
            try:
                spectral_calib_dict = self.DataHandling.calibration['spectral_calibration_fit']
            except:
                spectral_calib_dict = None
            self.measurement = ChirpCalibrationMeasurement(self.devices, background, self.grating_period_edit.value(), float(self.compression_carrier_wavelength_Qline.text()), float(self.chirp_step_Qline.text()), float(self.chirp_max_Qline.text()), float(self.chirp_min_Qline.text()), self.beam_name_box.currentText(), beam, spectral_calib_dict, demo=self.chirp_calib_demo_mode_checkbox.isChecked())
            self.temporalfitting = FitTemporalBeamCalibration(boundaries=[self.chirp_min_wavelength_value.value(),self.chirp_max_wavelength_value.value()])
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.send_chirp.connect(self.ChirpCalibrationPlot.set_data)
            self.measurement.send_beam.connect(self.DataHandling.set_beam)
            self.temporalfitting.send_chirp_calibration_data.connect(self.DataHandling.add_calibration)
            self.temporalfitting.send_chirp_region.connect(self.ChirpSelectionPlot.set_data)
            self.temporalfitting.send_chirp_fit.connect(self.ChirpFitplot.set_data)
            self.temporalfitting.send_polynomial.connect(self.ChirpFitplot.set_fit)
            self.temporalfitting.send_chirp_calibration_fit.connect(self.DataHandling.add_calibration)
            self.measurement.send_chirp_calibration_data.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def applySNRthreshold(self):
        '''
            Apply the SNR on the chirp scan and show the desired wavelength bandwidth.
        '''
        if hasattr(self, 'temporalfitting'):
            temporal_calib_dict = self.DataHandling.calibration['chirp_calibration_raw_data_beam_'+self.beam_name_box.currentText()]
            self.temporalfitting.set_SNR(temporal_calib_dict, self.chirp_SNR_threshold_value.value(),self.beam_name_box.currentText())
    
    def update_temporal_calibration_boundaries(self):
        '''
            Updates the boundaries to consider when processing temporal calibration data
        ''' 
        if hasattr(self, 'temporalfitting'):
            temporal_calib_dict = self.DataHandling.calibration['chirp_calibration_raw_data_beam_'+self.beam_name_box.currentText()]
            try: 
                self.temporalfitting.set_boundaries(temporal_calib_dict, [self.chirp_min_wavelength_value.value(), self.chirp_max_wavelength_value.value()], self.chirp_SNR_threshold_value.value(),self.beam_name_box.currentText())
            except KeyError:
                print('Unexpected error. There should be a temporal_calibration_raw_data key in the calibration dict in Datahandling')

    def fitChirpMeasurement(self):
        '''
            Fit the chirp scan to a polynomial function.
        ''' 
        if hasattr(self, 'temporalfitting'):
            temporal_calib_dict = self.DataHandling.calibration['chirp_calibration_processed_data_beam_'+self.beam_name_box.currentText()]
            phase_derivative_coeffs = self.temporalfitting.fit_chirp_scan(temporal_calib_dict['wavelengths'], temporal_calib_dict['chirps'], temporal_calib_dict['data'], self.chirp_polynomial_order_value.value(), float(self.compression_carrier_wavelength_Qline.text()),self.beam_name_box.currentText())
            # The fit describes GDD as an ordinary power series. Beam stores the
            # corresponding spectral-phase derivatives, so terms of order i in
            # the GDD fit must be multiplied by i! before they are assigned.
            # Generate names dynamically
            names = ["GDD" if i == 0 else "TOD" if i == 1 else "FOD" if i == 2 else f"{i+2}OD" for i in range(len(phase_derivative_coeffs))]
            # Polynomial string using the same names list
            poly_eq = " + ".join(names[i] + ("" if i == 0 else " * x" if i == 1 else f" * x^{i}") for i in range(len(phase_derivative_coeffs)))
            # Lines with coefficients using the same names
            lines = [f"Equation: {poly_eq}", ""] + [f"{names[i]} = {v:.2e} {'fs^2' if i == 0 else f'fs^{i+2}'}" for i, v in enumerate(phase_derivative_coeffs)]
            self.chirp_coeff.setText('\n'.join(lines))
            self.last_temp_fit_coeffs = np.array(np.concatenate(([0, 0], phase_derivative_coeffs)))

    def assignTemporalCalibration(self, Add_or_Remove):
        '''
            Assign the polynomial calibration to the beam.
        ''' 
        beam = self.DataHandling.get_beams()[self.beam_name_box.currentText()]
        beam.set_compressionCarrierWave(float(self.compression_carrier_wavelength_Qline.text()) * 10**(-9))
        self.last_temp_fit_coeffs = np.rint(self.last_temp_fit_coeffs).astype(int)
        old_coeff = beam.get_optimalPhase(units_to_return='fs').coef
        if len(self.last_temp_fit_coeffs) < len(old_coeff):
            self.last_temp_fit_coeffs = np.pad(self.last_temp_fit_coeffs, (0, len(old_coeff) - len(self.last_temp_fit_coeffs)), 'constant', constant_values=0)
        elif len(old_coeff) < len(self.last_temp_fit_coeffs):
            old_coeff = np.pad(old_coeff, (0, len(self.last_temp_fit_coeffs) - len(old_coeff)), 'constant', constant_values=0)
        beam.set_optimalPhase(P(Add_or_Remove*self.last_temp_fit_coeffs+old_coeff), )
        self.DataHandling.set_beam((self.beam_name_box.currentText(), beam))

    def spectralBeamCalibrationMeasurement(self):
        '''
             Sets up and starts a spectral Beam Calibration.
        '''
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement= SpectralBeamCalibrationMeasurement(self.devices,self.grating_period_edit.value(),self.column_increment_spinbox.value(),self.column_width_spinbox.value(),demo=self.spatial_calib_demo_mode_checkbox.isChecked())
            self.spectralfitting=FitSpectralBeamCalibration(boundaries=[self.shortest_fitting_wave_spin_box.value(),self.longest_fitting_wave_spin_box.value()],increment=self.column_increment_spinbox.value())

            self.spectralfitting.spec_wl_bounds = (
                self.SpecCalib_min_wavelength.value(),
                self.SpecCalib_max_wavelength.value()
            )

            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.send_intensities.connect(self.SpectralCalibDataPlot.set_data)
            self.measurement.send_intensities.connect(self.spectralfitting.extractMaxima)
            self.spectralfitting.send_spectral_calibration_data.connect(self.DataHandling.add_calibration)
            self.spectralfitting.send_maxima.connect(self.SpectralCalibrationFitPlot.set_data)
            self.spectralfitting.send_polynomial.connect(self.SpectralCalibrationFitPlot.set_fit)
            self.spectralfitting.send_spectral_calibration_fit.connect(self.DataHandling.add_calibration)
            self.measurement.send_spectral_calibration_data.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())

    def update_spectra_calibration_boundaries(self):
        '''
            Updates the boundaries to consider when processing spectral calibration data
        '''
        try:
            self.spectralfitting.set_boundaries([self.shortest_fitting_wave_spin_box.value(),self.longest_fitting_wave_spin_box.value()])
            try:
                spectral_calib_dict=self.DataHandling.calibration['spectral_calibration_raw_data']
                self.spectralfitting.extractMaxima(spectral_calib_dict['columns'],spectral_calib_dict['wavelengths'],spectral_calib_dict['data'])
            except KeyError:
                print('Unexpected error. There should be a spectral_calibration_raw_data key in the calibration dict in Datahandling')
        except AttributeError:
            self.spectralfitting=FitSpectralBeamCalibration(boundaries=[self.shortest_fitting_wave_spin_box.value(),self.longest_fitting_wave_spin_box.value()])

    def fit_spectral_calibration(self):
        '''
            Fits the last spectral beam calibration data using the displayed valued and updates the result in the Datahandling thread.
        '''
        try:
            spectral_calib_dict=self.DataHandling.calibration['spectral_calibration_processed_data']
            try:
                self.spectralfitting.fitSpectraMaxima(spectral_calib_dict['columns'],spectral_calib_dict['wavelengths'],self.spectral_fit_polynomial_order_spinbox.value())
            except AttributeError:
                self.spectralfitting=FitSpectralBeamCalibration(boundaries=[self.shortest_fitting_wave_spin_box.value(),self.longest_fitting_wave_spin_box.value()])
        except KeyError:
            logger.warning('%s Spectral calibration data has not been processed. Run a spectral beam calibration measurement first'%datetime.datetime.now())
    
    def assign_spectral_calibration(self):
        '''
            Saves the current spectral beam calibration fit and parameters to the calibration thread
        '''
        beam_dict=self.DataHandling.get_beams()
        if beam_dict=={}:
            beam_dict={'ALL':Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())}
        for key in beam_dict:
            beam_dict[key].set_pixelToWavelength(self.DataHandling.calibration['spectral_calibration_fit'])
            beam_dict[key].set_beamHorizontalDelimiters(self.DataHandling.calibration['spectral_calibration_fit'].domain.astype(int))
            self.DataHandling.set_beam((key,beam_dict[key]))

    def delayAcquireMeasurement(self):
        """
            Start a cross correlation measurement between two beams
        """
        if not self.measurement_busy:
            self.measurement_busy = True
            if self.delay_reference_beam_name_box.currentText() == self.delay_second_beam_name_box.currentText():
                print('Measurement not started, beams need to be different')
                return
            if self.delay_reference_beam_name_box.currentText() in self.DataHandling.get_beams():
                refBeam = self.DataHandling.get_beams()[self.delay_reference_beam_name_box.currentText()]
            else:
                refBeam = Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())
            if self.delay_second_beam_name_box.currentText() in self.DataHandling.get_beams():
                secBeam = self.DataHandling.get_beams()[self.delay_second_beam_name_box.currentText()]
            else:
                secBeam = Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())
            
            self.DataHandling.clear_data() 
            if hasattr(self, 'background'):
                delayBackground = self.DataHandling.calibration['background_data']
                background = delayBackground['spec']
            else:
                background = 0
            
            try:
                spectral_calib_dict = self.DataHandling.calibration['spectral_calibration_fit']
            except:
                spectral_calib_dict = None
            
            self.measurement = DelayCalibrationMeasurement(
                self.devices, background, self.grating_period_edit.value(), 
                float(self.delay_carrier_wavelength_value.text()), 
                float(self.delay_step_group_delay_value.text()), 
                float(self.delay_max_group_delay_value.text()), 
                float(self.delay_min_group_delay_value.text()), 
                self.delay_reference_beam_name_box.currentText(),
                self.delay_second_beam_name_box.currentText(), 
                refBeam, secBeam, spectral_calib_dict, 
                demo=self.delay_demo_mode_checkbox.isChecked())
            
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendBeam.connect(self.DataHandling.set_beam)
            self.measurement.sendCrossCorrelation.connect(self.DelayCalibrationPlot.set_data)
            self.measurement.sendCrossCorrelationData.connect(self.DataHandling.add_calibration)
            self.measurement.sendCrossCorrelationRegion.connect(self.DelayFitPlot.set_data)
            self.measurement.sendCrossCorrelationRegionData.connect(self.DataHandling.add_calibration)
            self.measurement.sendCrossCorrelationRegionFit.connect(self.DelayFitPlot.set_fit)
            self.measurement.sendCrossCorrelationRegionFitData.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def delayApplySNRThreshold(self):
        '''
            Apply the SNR on the chirp scan and show the desired wavelength bandwidth.
        '''
        self.refBeamName = self.delay_reference_beam_name_box.currentText()
        self.secBeamName = self.delay_second_beam_name_box.currentText()

        key = f'Delay_calibration_raw_data_{self.refBeamName}_{self.secBeamName}'
        if key in self.DataHandling.calibration:
            delay_calib_dict = self.DataHandling.calibration[key]
            self.measurement.set_SNR(delay_calib_dict, self.delay_SNR_threshold_value.value(), [self.delay_min_wavelength_bandwidth_value.value(), self.delay_max_wavelength_bandwidth_value.value()])
        else:
            logger.warning('%s Delay calibration data has not been taken. Run a delay beam calibration measurement first'%datetime.datetime.now())

    def delayFitMeaserement(self):
        '''
            Fits the last delay beam calibration data using the displayed valued and updates the result in the Datahandling thread.
        '''
        if 'delay_calibration_processed_data' in self.DataHandling.calibration:
            delay_calib_processed_dict = self.DataHandling.calibration['delay_calibration_processed_data']
            self.measurement.get_fit(delay_calib_processed_dict['delay'], delay_calib_processed_dict['data'])
        else:
            logger.warning('%s Delay calibration data has not been processed. Processed the calibration measurement first'%datetime.datetime.now())

    def assignDelayCalibration(self, Add_or_Remove):
        '''
            Assign the delay calibration to the beam.
        ''' 
        if 'delay_calibration_processed_data_fit' in self.DataHandling.calibration:
            delay_calib_processed_fit_dict = self.DataHandling.calibration['delay_calibration_processed_data_fit']
            mu = delay_calib_processed_fit_dict['mu']
            beam = self.DataHandling.get_beams()[self.delay_second_beam_name_box.currentText()]
            beam.set_delayCarrierWave(float(self.delay_carrier_wavelength_value.text()) * 10**(-9))
            old_coeff = beam.get_optimalPhase(units_to_return='fs').coef
            old_coeff[1] += Add_or_Remove*mu
            beam.set_optimalPhase(P(old_coeff))
            self.DataHandling.set_beam((self.delay_second_beam_name_box.currentText(), beam))
        else:
            logger.warning('%s Delay calibration fit has not been processed. Processed the calibration fit first'%datetime.datetime.now())

    def _resolve_tgfrog_beam_names(self, is_demo):
        """
            Reads the three beam-role dropdowns in the Pulse characterization tab. In demo
            mode, empty/duplicate selections fall back to placeholder names since
            TGFROGMeasurement's demo mode never touches the beam objects; for real hardware,
            the three must be distinct and selected. Shared by the acquire and retrieve
            handlers so the two can't drift out of sync on what counts as valid.
            output:
                - (probeBeamName, gratingBeam1Name, gratingBeam2Name), or None (with an error
                  already shown in the status label) if invalid for the current mode
        """
        pc = self.PulseCharacterization
        probeBeamName = pc.probe_beam_box.currentText()
        gratingBeam1Name = pc.grating_beam1_box.currentText()
        gratingBeam2Name = pc.grating_beam2_box.currentText()

        if is_demo:
            probeBeamName = probeBeamName or 'SimProbe'
            gratingBeam1Name = gratingBeam1Name or 'SimGrating1'
            gratingBeam2Name = gratingBeam2Name or 'SimGrating2'
            return probeBeamName, gratingBeam1Name, gratingBeam2Name

        if ('' in (probeBeamName, gratingBeam1Name, gratingBeam2Name)
                or len({probeBeamName, gratingBeam1Name, gratingBeam2Name}) < 3):
            pc.status_label.setText(
                'Error: select three different beams for a real acquisition.')
            return None
        return probeBeamName, gratingBeam1Name, gratingBeam2Name

    def tgfrogAcquireMeasurement(self):
        """
            Starts a TG-FROG delay scan using the beam roles and scan parameters set in the
            Pulse characterization tab.
        """
        if not self.measurement_busy:
            self.measurement_busy = True
            pc = self.PulseCharacterization
            is_demo = pc.demo_mode_checkbox.isChecked()

            names = self._resolve_tgfrog_beam_names(is_demo)
            if names is None:
                self.measurement_busy = False
                return
            probeBeamName, gratingBeam1Name, gratingBeam2Name = names

            beam_dict = self.DataHandling.get_beams()
            probeBeam = beam_dict[probeBeamName] if probeBeamName in beam_dict else Beam(self.devices['SLM'].get_width(), self.devices['SLM'].get_height())
            gratingBeam1 = beam_dict[gratingBeam1Name] if gratingBeam1Name in beam_dict else Beam(self.devices['SLM'].get_width(), self.devices['SLM'].get_height())
            gratingBeam2 = beam_dict[gratingBeam2Name] if gratingBeam2Name in beam_dict else Beam(self.devices['SLM'].get_width(), self.devices['SLM'].get_height())

            self.DataHandling.clear_data()
            if hasattr(self, 'background'):
                tgfrogBackground = self.DataHandling.calibration['background_data']
                background = tgfrogBackground['spec']
            else:
                background = 0

            try:
                spectral_calib_dict = self.DataHandling.calibration['spectral_calibration_fit']
            except KeyError:
                spectral_calib_dict = None

            self.measurement = TGFROGMeasurement(
                self.devices, background, self.grating_period_edit.value(),
                pc.probe_wavelength_spin.value(),
                pc.delay_step_spin.value(),
                pc.delay_max_spin.value(),
                pc.delay_min_spin.value(),
                probeBeamName, gratingBeam1Name, gratingBeam2Name,
                probeBeam, gratingBeam1, gratingBeam2,
                spectral_calib_dict,
                demo=is_demo,
                demo_fwhm=pc.sim_fwhm_spin.value() * 1e-15,
                demo_gdd=pc.sim_gdd_spin.value() * 1e-30,
                demo_tod=pc.sim_tod_spin.value() * 1e-45,
                demo_noise_level=pc.sim_noise_spin.value() / 100.0,
                demo_window_nm=pc.sim_window_spin.value())

            """ sendSpectrum is deliberately not wired to DataHandling.concatenate_data here,
            unlike other measurements: that buffer assumes every emitted spectrum has the same
            length as DataHandling.spec_length (the currently configured spectrometer's pixel
            count), but demo mode synthesizes its own wavelength axis at a different length,
            which crashed concatenate_data's np.c_ concatenation when tested. The 2D trace is
            already fully captured below via sendTraceData, which is what matters for retrieval. """
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendBeam.connect(self.DataHandling.set_beam)
            self.measurement.sendTrace.connect(self.PulseCharacterization.set_data)
            self.measurement.sendTraceData.connect(self.DataHandling.add_calibration)
            self.measurement.finished.connect(lambda: self.PulseCharacterization.set_running(False))
            self.PulseCharacterization.set_running(True)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def tgfrogRetrieveMeasurement(self):
        """
            Runs offline TG-FROG retrieval (TGFROGRetrievalWorker) on the trace matching the
            beam roles currently selected in the Pulse characterization tab. Not gated on
            measurement_busy: retrieval is pure computation on an already-acquired trace, it
            does not touch the SLM or spectrometer, so it neither needs nor should block a
            hardware acquisition running at the same time.
        """
        pc = self.PulseCharacterization
        is_demo = pc.demo_mode_checkbox.isChecked()
        names = self._resolve_tgfrog_beam_names(is_demo)
        if names is None:
            return
        probeBeamName, gratingBeam1Name, gratingBeam2Name = names

        key = f'TGFROG_raw_data_{probeBeamName}_{gratingBeam1Name}_{gratingBeam2Name}'
        if key not in self.DataHandling.calibration:
            pc.status_label.setText(
                f'No trace found for these beam roles ({key}). Run a scan or simulation first.')
            return

        trace = self.DataHandling.calibration[key]
        self.tgfrog_retrieval_worker = TGFROGRetrievalWorker(trace)
        self.tgfrog_retrieval_worker.sendResult.connect(pc.set_retrieval_result)
        self.tgfrog_retrieval_worker.sendError.connect(pc.set_retrieval_error)
        self.tgfrog_retrieval_worker.finished.connect(lambda: pc.set_retrieval_running(False))
        pc.set_retrieval_running(True)
        self.tgfrog_retrieval_worker.start()

    def getLOSpectrum(self):
        if not self.measurement_busy:
            self.measurement_busy = True
            beam_name = 'LO'
            beam = self.DataHandling.get_beams()[beam_name]
            self.measurement = AcquireLO(self.devices, beam_name, beam)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendSpectrum.connect(self.LOspectrumPlot.set_data)
            self.measurement.sendLOData.connect(self.DataHandling.add_calibration)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendBeam.connect(self.DataHandling.set_beam)
            self.measurement.start()
    
    def MDCSacquireMeasurement(self):
            scannedDelay = np.arange(float(self.MDCS_scanned_delay_min_value.text()), float(self.MDCS_scanned_delay_max_value.text()), float(self.MDCS_scanned_delay_step_value.text()), dtype=int)
            secondaryDelay = np.arange(float(self.MDCS_secondary_delay_min_value.text()), float(self.MDCS_secondary_delay_max_value.text()), float(self.MDCS_secondary_delay_step_value.text()), dtype=int)
            beam_dict = self.DataHandling.get_beams()
            beam_name = list(beam_dict.keys())
            self._cached_filename = None
            if 'LO_data' in self.DataHandling.calibration:
                LO_spectrum = self.DataHandling.calibration['LO_data']
                self.measurement = BoxcarGeometry(self.devices, 
                    self.MDCS_measurement_type_box.currentText(),
                    float(self.MDCS_TLO_delay_value.text()),
                    scannedDelay,
                    secondaryDelay,
                    beam_name,
                    beam_dict,
                    LO_spectrum['spec'],
                    self.filename, 
                    self.comments_edit.toPlainText(),
                    phase_cycling=self.MDCS_phase_cycling_checkbox.isChecked(),
                    demo=self.MDCS_demo_mode_checkbox.isChecked())
                self.measurement.sendProgress.connect(self.set_progress)
                self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
                self.measurement.sendPhaseCycling.connect(self.LOspectrumPlot.set_data)
                self.measurement.sendBeam.connect(self.DataHandling.set_multiple_beams)
                self.measurement.sendMDCSPlot.connect(self.MDCSplot.set_data)
                self.measurement.sendMDCSRaw.connect(self.DataHandling.add_calibration)
                self.measurement.sendSave.connect(lambda: self.save_calibration(filename_prefix=self.filename, use_prompt=False, save_dir=self.save_folder_path))
                self.measurement.sendFourierReal.connect(self.MDCSFourierRealPlot.set_data)
                self.measurement.sendFourierImag.connect(self.MDCSFourierImagPlot.set_data)
                self.measurement.start()
            else:
                logger.warning('%s Get the local oscillotor plot before running an acquisition.'%datetime.datetime.now())

    def stop_measurement(self):
        # stop measurement
        self.measurement.stop()
        self.measurement_busy = False

    def Measure_LUT_PhasetoGreyscale(self):
        '''
                    Sets up and starts a Phase to Greyscale LUT Measurement.
        '''

        if not self.measurement_busy:
            logger.info('%s Start LUT Calibration Measurement' % datetime.datetime.now())
            print('Start LUT Calibration Measurement')
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = Measure_LUT_PhasetoGreyscale(self.devices, self.parameter, self.LUT_grating_period.value(), self.LUT_calib_central_wavelength.value())
            self.measurement.sendProgress.connect(self.set_progress)
            self.DataHandling.sendSpectrum.connect(self.LUT_Calib_plot.set_data)

            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendIntensity.connect(self.LUT_Calib_plot_2.add_data)
            self.measurement.sendCalib.connect(self.DataHandling.add_calibration)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.sendSave.connect(lambda: self.save_calibration(filename_prefix=self.filename, use_prompt=False, save_dir=self.save_folder_path))
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy' % datetime.datetime.now())
            #print('Measurement not started, devices are busy')

    def Generate_LUT_PhasetoGreyscale(self):
        '''
                    Analyzes measured spectrum file and generates a Phase to Greyscale LUT File.
        '''

        if not self.measurement_busy:
            if 'LUT_calib' in self.DataHandling.calibration:
                LUT_calib = self.DataHandling.calibration['LUT_calib']
                grayscale = LUT_calib['greyscale']
                intensity = LUT_calib['I_norm']
                logger.info('%s Start LUT Generation' % datetime.datetime.now())
                print('Start LUT File Generation')
                self.measurement_busy = True
                self.DataHandling.clear_data()
                self.measurement = Generate_LUT_PhasetoGreyscale(self.devices, self.parameter, [self.LUT_calib_0.value(), self.LUT_calib_2pi.value()], grayscale, intensity)
                self.measurement.sendProgress.connect(self.set_progress)
                self.measurement.sendLine.connect(self.LUT_Calib_plot_2.draw_line)
                self.measurement.sendPhase.connect(self.LUT_Calib_plot_2.add_data)
                self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy' % datetime.datetime.now())
            #print('Measurement not started, devices are busy')

    def Load_LUT_PhasetoGrayscale(self):
        '''
                    Ask the user which LUT file to load. 
        '''
        LUT_FilePath = self.devices['SLM'].load_LUT()
        LUT_FilePath = ('LUT_FilePath', LUT_FilePath)
        self.DataHandling.add_calibration(LUT_FilePath)
    
    def show_beam_explorer(self):
        """
            Shows the beam explorer if it is not already shown
        """
        logger.info('%s'%self.beam_explorer)
        self.beam_explorer.show()
    
    def assign_demo_beams(self):
        """
            Assigns some beams to the DataHandling to test the BeamExplorer
        """
        labels=['LO','A','B','C']
        demo_beam_dict={}
        for i,label in enumerate(labels):
            demo_beam=Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())
            demo_beam.set_optimalPhase(P([0,100,2000,3000,-400]))
            demo_beam.set_gratingPeriod(25)
            demo_beam.set_beamVerticalDelimiters([i*300,(i+1)*300-1])
            demo_beam_dict[label]=demo_beam
        [self.DataHandling.set_beam((beamname,beam)) for beamname,beam in demo_beam_dict.items()]


    def closeEvent(self,event):
        '''
            Closes all windows when the main window is closed.
        '''
        QApplication.closeAllWindows()

    def save_calibration(self, filename_prefix="Filename", use_prompt=True, save_dir=None):
        """
        Save all Beam objects and calibration data.
        """

        # Convert all Beam objects to safe dictionaries
        beam_dicts = {name: Beam.beam_to_dict(beam) for name, beam in self.DataHandling.beams.items()}

        # Convert calibration data to safe dict
        calibration_dict = DataHandling.calibration_to_dict(self.DataHandling.calibration)

        data_to_save = {
            "beams": beam_dicts,
            "calibration": calibration_dict
        }

        if use_prompt:
            HDF5Helper.save_to_hdf5_with_prompt(data_to_save, default_filename=filename_prefix)
        else:
            if save_dir is None:
                raise ValueError("save_dir must be provided if use_prompt=False")
            
            # Create filename ONCE, reuse on later saves
            if not hasattr(self, "_cached_filename") or self._cached_filename is None:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                self._cached_filename = f"{filename_prefix}_{timestamp}.h5"

            default_filename = self._cached_filename

            HDF5Helper.save_to_hdf5(data_to_save, save_dir, default_filename)

    def load_calibration(self):
        """
            Load beams and calibration from HDF5 file using prompt-based loader.
            - Beams are reconstructed using Beam.dict_to_beam
            - Calibration Polynomials are restored automatically
        """
        # Load the top-level dictionary from HDF5
        loaded_data = HDF5Helper.load_from_hdf5_prompt()
        if loaded_data is None:
            print("No data loaded.")
            return
        # Load beams
        beams_loaded = loaded_data.get("beams", {})
        for name, beam_dict in beams_loaded.items():
            beam_obj = Beam.dict_to_beam(
                beam_dict=beam_dict,
                beam_class=Beam,
                slm_width=self.devices['SLM'].get_width(),
                slm_height=self.devices['SLM'].get_height()
            )
            self.DataHandling.beams[name] = beam_obj
            self.DataHandling.set_beam((name, beam_obj))

        # Load calibration
        calibration_loaded = loaded_data.get("calibration", {})
        self.DataHandling.calibration = DataHandling.dict_to_calibration(calibration_loaded)

        LUT_FilePath = self.DataHandling.calibration['LUT_FilePath']
        self.devices['SLM'].load_LUT(LUT_FilePath)
        self.assign_spectral_calibration()
        print("Calibration and beams successfully loaded.")

class HDF5Helper:

    @staticmethod
    def save_to_hdf5_with_prompt(data, default_filename="data.h5"):
        """
            Open a file dialog to choose filename and save HDF5 file.

            Parameters:
            - data (dict): Nested dictionary of data to save.
            - default_filename (str): Suggested default file name.
        """

        # Initialize Tkinter root and hide it
        root = tk.Tk()
        root.withdraw()

        # Ask user for filename and location
        filepath = filedialog.asksaveasfilename(
            title="Save HDF5 file as",
            defaultextension=".hdf5",
            initialfile=default_filename,
            filetypes=[("HDF5 files", "*.hdf5 *.h5"), ("All files", "*.*")]
        )

        if not filepath:
            print("Save cancelled.")
            return

        # Remove existing file if present
        if os.path.exists(filepath):
            os.remove(filepath)

        # Save data recursively
        with h5py.File(filepath, 'w') as h5f:
            HDF5Helper._recursively_save(h5f, '', data)

        print(f"Data saved to {filepath}")

    @staticmethod
    def save_to_hdf5(data, filepath, filename):
        """
            Save nested dictionary to HDF5 file at specified location.

            Parameters:
            - data (dict): Nested dictionary to save.
            - filepath (str): Directory where file will be saved.
            - filename (str): File name (with or without extension).
        """

        os.makedirs(filepath, exist_ok=True)

        # Add extension if missing
        base, ext = os.path.splitext(filename)
        if ext == '':
            ext = '.h5'
        full_path = os.path.join(filepath, base + ext)

        if os.path.exists(full_path):
            os.remove(full_path)

        # Save recursively
        with h5py.File(full_path, 'w') as h5f:
            HDF5Helper._recursively_save(h5f, '', data)

        print(f"Data saved to {full_path}")

    @staticmethod
    def _recursively_save(h5file, path, dic):
        """Recursively save a nested dictionary to HDF5."""
        import os
        for key, item in dic.items():
            key_path = f"{path}/{key}" if path else key
            if isinstance(item, dict):
                # Recurse into sub-dictionaries
                HDF5Helper._recursively_save(h5file, key_path, item)
            else:
                # Ensure intermediate group exists
                group_path = os.path.dirname(key_path)
                if group_path and group_path not in h5file:
                    h5file.require_group(group_path)
                # Save dataset
                h5file.create_dataset(key_path, data=item)

    @staticmethod
    def load_from_hdf5_prompt():
        """
            Open a file dialog to load an HDF5 file.

            Returns:
            - dict: Nested dictionary of loaded data.
        """

        root = tk.Tk()
        root.withdraw()

        full_path = filedialog.askopenfilename(
            title="Choose HDF5 file to open",
            filetypes=[("HDF5 files", "*.hdf5 *.h5"), ("All files", "*.*")]
        )

        if not full_path:
            print("Load cancelled.")
            return None

        filepath, filename = os.path.split(full_path)
        return HDF5Helper.load_from_hdf5(filepath, filename)

    @staticmethod
    def load_from_hdf5(filepath, filename):
        """
            Load HDF5 file as nested dictionary, preserving types.

            Parameters:
            - filepath (str): Directory where file is located.
            - filename (str): HDF5 file name.

            Returns:
            - dict: Nested dictionary with native Python types for scalars.
        """

        base, ext = os.path.splitext(filename)
        if ext == '':
            ext = '.h5'
        full_path = os.path.join(filepath, base + ext)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"No file found at: {full_path}")

        with h5py.File(full_path, 'r') as h5f:
            return HDF5Helper._recursively_load(h5f)

    @staticmethod
    def _recursively_load(h5group):
        """
            Recursively load data from HDF5 group into nested dictionary,
            converting NumPy scalars to native Python types.
        """

        result = {}
        for key, item in h5group.items():
            if isinstance(item, h5py.Group):
                result[key] = HDF5Helper._recursively_load(item)
            elif isinstance(item, h5py.Dataset):
                data = item[()]

                # Convert NumPy scalars to native Python
                if isinstance(data, (np.generic, np.bool_)):
                    data = data.item()

                # Decode bytes to string if needed
                if isinstance(data, bytes):
                    data = data.decode('utf-8')

                result[key] = data
        return result
    
class UpdateWorker(QtCore.QThread):

    new_parameter = QtCore.pyqtSignal(dict)

    def __init__(self, devices_dic, read_only):
        super(UpdateWorker, self).__init__()
        self.devices = devices_dic
        self.read_only = read_only
        self.stop = False
        self.updated_param = {}
        self.update_interval = 0.5

    def run(self):
        while not self.stop:
            i = 0
            for devices in self.devices.keys():
                for param in self.devices[devices].parameter_dict.keys():
                    if param in self.read_only:
                        self.updated_param[param] = self.devices[devices].parameter_dict[param]
                self.new_parameter.emit(self.updated_param)
            time.sleep(self.update_interval)

""" Every fixed pixel width/height in this app's widgets (spin boxes, panels, splitter sizes)
was chosen assuming Qt renders logical pixels 1:1 with the display. Without HiDPI awareness,
Qt5 on Windows does exactly that regardless of the monitor's actual scale factor, so the same
layout looks fine on a display running at 100% scaling and cramped/overlapping on a laptop
screen or any monitor scaled above that -- which is what made this so inconsistent to debug
from screenshots taken on different screens. Must be set before QApplication is constructed. """
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

app = QtWidgets.QApplication(sys.argv)
window = MainInterface()
app.exec_()
