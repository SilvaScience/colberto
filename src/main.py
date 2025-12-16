# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 14:34:11 2025
@author: David Tiede
"""

import sys
import time
import re
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
from GUI.MeasurementPlot import LOmeasurementPlot, MDCSmeasurementPlot
from GUI.LUT_Calib_plot import LUT_Calib_plot
from GUI.SLMDisplay import SLMDisplay
from DataHandling.DataHandling import DataHandling
from measurements.MeasurementClasses import AcquireMeasurement,RunMeasurement,BackgroundMeasurement, ViewMeasurement
from measurements.MDCSClasses import AcquireLO, BoxcarGeometry
from measurements.CalibrationClasses import VerticalBeamCalibrationMeasurement, SpectralBeamCalibrationMeasurement, FitSpectralBeamCalibration, AcquireBackground, ChirpCalibrationMeasurement, FitTemporalBeamCalibration, DelayCalibrationMeasurement
from measurements.Calibration_Classes import Measure_LUT_PhasetoGreyscale,Generate_LUT_PhasetoGreyscale
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

        
        self.devices = load_instruments()

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

        # LUT Calibration - Utilities
        self.LUT_calibration_box = self.findChild(QtWidgets.QGroupBox, 'LUT_calibration')
        self.LUT_int_time_box = self.findChild(QtWidgets.QDoubleSpinBox, 'LUT_int_time_doubleSpinBox')
        self.LUT_calib_spectra_avg_box = self.findChild(QtWidgets.QSpinBox, 'LUT_calib_spectra_avg_spinBox')
        self.LUT_calib_scans_number_box = self.findChild(QtWidgets.QSpinBox, 'LUT_calib_scans_number_spinBox')
        self.LUT_calib_plot_layout = self.findChild(pg.PlotWidget, 'LUT_calib_plot_layout')
        self.measure_LUT_calib_button = self.findChild(QtWidgets.QPushButton, 'measure_LUT_calib')
        self.select_LUT_Data_file_button = self.findChild(QtWidgets.QPushButton, 'select_LUT_Data_file_pushButton')
        self.LUT_Data_file_edit = self.findChild(QtWidgets.QLineEdit, 'LUT_Data_file_lineEdit')
        self.generate_LUT_calib_button = self.findChild(QtWidgets.QPushButton, 'generate_LUT_calib')
        #SLM Related
        self.slm_display=self.findChild(pg.GraphicsLayoutWidget,'slm_display')
        
        # initial parameter values, retrieved from devices
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for device in self.devices.keys():
            self.parameter_dic[device] = self.devices[device].parameter_display_dict

        # create parameter array for easy access
        self.create_parameter_array()

        # add items to GUI
        self.SpectrometerPlot = SpectrometerPlot()
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.SpectrometerPlot)
        self.spectro_tab.setLayout(vbox)
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
        self.LUT_Calib_plot = LUT_Calib_plot(self.LUT_calib_plot_layout)
        self.slm_display_plot= SLMDisplay(self.slm_display)

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
                child =QtWidgets.QTreeWidgetItem()
                item.addChild(child)
                name_widget = QtWidgets.QLabel(param)
                self.parameter_widgets[param] = QtWidgets.QDoubleSpinBox()
                #self.parameter_widgets[param].setFixedSize(self.parameter_widgets[param].__sizeof__(), 16)
                self.parameter_widgets[param].setReadOnly(self.parameter_dic[device][param]['read'])
                try:
                    self.parameter_widgets[param].setSuffix(self.parameter_dic[device][param]['unit'])
                    self.parameter_widgets[param].setMaximum(self.parameter_dic[device][param]['max'])
                except:
                    pass
                try:
                    self.parameter_widgets[param].setMinimum(self.parameter_dic[device][param]['min'])
                except:
                    pass
                if self.parameter_dic[device][param]['read']:
                    self.readonly_parameter.append(param)
                else:
                    self.parameter_widgets[param].setValue(self.parameter_dic[device][param]['val'])
                    self.parameter_widgets[param].editingFinished.connect(partial(self.set_parameter,param))
                    self.writeonly_parameter.append(param)
                self.parameter_tree.setItemWidget(child, 0, name_widget)
                self.parameter_tree.setItemWidget(child, 1, self.parameter_widgets[param])

        # start DataHandling
        self.spec_length = self.devices['spectrometer'].get_num_pixel()
        self.DataHandling = DataHandling(self.parameter, self.spec_length)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        self.DataHandling.sendSpectrum.connect(self.SpectrometerPlot.set_data)
        self.DataHandling.sendMaximum.connect(self.SpectrometerPlot.update_datareader)

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
        self.measure_LUT_calib_button.clicked.connect(self.Measure_LUT_PhasetoGreyscale)  # measure spectrum
        self.select_LUT_Data_file_button.clicked.connect(self.load_LUT_Data_file)  # select spectrum data file
        self.generate_LUT_calib_button.clicked.connect(
        self.Generate_LUT_PhasetoGreyscale)  # use spectrum data to generate LUT file
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
        # Measurement tab connect events
        self.MDCS_getLO_button.clicked.connect(self.getLOSpectrum)
        self.MDCS_acquire_button.clicked.connect(self.MDCSacquireMeasurement)
        # SLM display connections
        self.devices['SLM'].slm_worker.imageSLM.connect(self.slm_display_plot.set_data)
        test_image=beam_image_gen()
        # Beam update connection
        self.DataHandling.sendBeams.connect(self.beam_explorer.receive_beams)
        self.DataHandling.sendBeams.connect(self.update_beam_name_list)
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

    def create_parameter_array(self):
        # initialization function to store all parameters in one array
        self.parameter = {}
        for devices in self.devices.keys():
            for param in self.devices[devices].parameter_dict.keys():
                self.parameter[param] = self.devices[devices].parameter_dict[param]

    def update_read_parameter(self, new_parameter):
        # update all read parameters
        for param in new_parameter.keys():
            self.parameter_widgets[param].setValue(new_parameter[param])
            self.parameter[param] = new_parameter[param]
        # send parameters to DataViewer
        self.DataHandling.update_parameter(list(self.parameter.values()))

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
        bg = np.loadtxt(bg_path, delimiter=',')
        self.DataHandling.background = bg[-self.spec_length:, 1]
        # logger.info(np.shape(bg[1:,1]))

        # display background filename
        idx = bg_path.rfind('/')
        self.bg_file_indicator.setText(bg_path[idx+1:])

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

    def load_LUT_Data_file(self):
        # open background file and set as background
        LUT_DataFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select LUT Data File')
        LUT_DataFile_path = LUT_DataFile[0]

        # display measured spectra filepath
        self.LUT_Data_file_edit.setText(LUT_DataFile_path)
        logger.warning('%s Data path stored' % datetime.datetime.now())

    ##### Measurements #####

    def acquire_measurement(self):
        # take one spectrum with spectrometer
        if self.measurement_busy:
            try:
                self.measurement.take_spectrum()
            except AttributeError:
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
            self.measurement.sendClear.connect(self.SpectrometerPlot.clear_plot)
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
            temporal_calib_dict = self.DataHandling.calibration['chirp_calibration_raw_data']
            self.temporalfitting.set_SNR(temporal_calib_dict, self.chirp_SNR_threshold_value.value())
    
    def update_temporal_calibration_boundaries(self):
        '''
            Updates the boundaries to consider when processing temporal calibration data
        ''' 
        if hasattr(self, 'temporalfitting'):
            temporal_calib_dict = self.DataHandling.calibration['chirp_calibration_raw_data']
            try: 
                self.temporalfitting.set_boundaries(temporal_calib_dict, [self.chirp_min_wavelength_value.value(), self.chirp_max_wavelength_value.value()], self.chirp_SNR_threshold_value.value())
            except KeyError:
                print('Unexpected error. There should be a temporal_calibration_raw_data key in the calibration dict in Datahandling')

    def fitChirpMeasurement(self):
        '''
            Fit the chirp scan to a polynomial function up to the fifth order.
        ''' 
        if hasattr(self, 'temporalfitting'):
            temporal_calib_dict = self.DataHandling.calibration['temporal_calibration_processed_data']
            coeffs = self.temporalfitting.fit_chirp_scan(temporal_calib_dict['wavelengths'], temporal_calib_dict['chirps'], temporal_calib_dict['data'], self.chirp_polynomial_order_value.value(), float(self.compression_carrier_wavelength_Qline.text()))
            coeffs_scaled = [coeffs[i] * (10**15)**i for i in range(len(coeffs))]
            # Generate names dynamically
            names = ["GDD" if i == 0 else "TOD" if i == 1 else "FOD" if i == 2 else f"{i+2}OD" for i in range(len(coeffs))]
            # Polynomial string using the same names list
            poly_eq = " + ".join(names[i] + ("" if i == 0 else " * x" if i == 1 else f" * x^{i}") for i in range(len(coeffs)))
            # Lines with coefficients using the same names
            lines = [f"Equation: {poly_eq}", ""] + [f"{names[i]} = {v:.2e} {'fs^2' if i == 0 else f'fs^{i+2}'}" for i, v in enumerate(coeffs_scaled)]
            self.chirp_coeff.setText('\n'.join(lines))
            self.last_temp_fit_coeffs = np.array(np.concatenate(([0, 0], coeffs_scaled)))

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
        beam.set_optimalPhase(P(Add_or_Remove*self.last_temp_fit_coeffs+old_coeff))
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
            self.measurement.sendCrossCorreletionRegion.connect(self.DelayFitPlot.set_data)
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
        if 'Delay_calibration_raw_data' in self.DataHandling.calibration:
            delay_calib_dict = self.DataHandling.calibration['Delay_calibration_raw_data']
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
                self.measurement.sendBeam.connect(self.DataHandling.set_multiple_beams)
                self.measurement.sendMDCSPlot.connect(self.MDCSplot.set_data)
                self.measurement.sendMDCSRaw.connect(self.DataHandling.add_calibration)
                print(self.filename)
                self.measurement.sendSave.connect(lambda: self.save_calibration(filename_prefix=self.filename, use_prompt=False, save_dir=self.save_folder_path))
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
            self.measurement = Measure_LUT_PhasetoGreyscale(self.devices, self.parameter, self.LUT_int_time_box.value(),
                                                            self.LUT_calib_spectra_avg_box.value(),
                                                            self.LUT_calib_scans_number_box.value())
            self.measurement.sendProgress.connect(self.set_progress)
            self.DataHandling.sendSpectrum.connect(self.LUT_Calib_plot.set_data)

            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy' % datetime.datetime.now())
            #print('Measurement not started, devices are busy')

    def Generate_LUT_PhasetoGreyscale(self):
        '''
                    Analyzes measured spectrum file and generates a Phase to Greyscale LUT File.
        '''

        if not self.measurement_busy:
            logger.info('%s Start LUT Generation' % datetime.datetime.now())
            print('Start LUT File Generation')
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = Generate_LUT_PhasetoGreyscale(self.devices, self.parameter, self.LUT_Data_file_edit.text())
            self.measurement.sendProgress.connect(self.set_progress)

            self.measurement.start()
        else:
            logger.info('%s Measurement not started, devices are busy' % datetime.datetime.now())
            #print('Measurement not started, devices are busy')
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
            HDF5Helper.save_to_hdf5_with_prompt(data_to_save, default_filename=default_filename)
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

app = QtWidgets.QApplication(sys.argv)
window = MainInterface()
app.exec_()
