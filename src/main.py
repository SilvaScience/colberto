# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 14:34:11 2025
@author: David Tiede
"""

import sys
import time
import re
import os
from collections import defaultdict
from pathlib import Path
import numpy as np
from PyQt5 import QtCore, QtWidgets, uic
from functools import partial
import pyqtgraph as pg
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from GUI.VerticalCalibPlot import VerticalCalibPlot 
from GUI.SpectralCalibPlot import SpectralCalibDataPlot,SpectralCalibFitPlot
from drivers.CryoDemo import CryoDemo
from drivers.SpectrometerDemo_advanced import SpectrometerDemo
from drivers.SLMDemo import SLMDemo
from drivers.StresingDemo import StresingDemo
from drivers.MonochromDemo import MonochromDemo
from DataHandling.DataHandling import DataHandling
from measurements.MeasurementClasses import AcquireMeasurement,RunMeasurement,BackgroundMeasurement, ViewMeasurement
from measurements.CalibrationClasses import VerticalBeamCalibrationMeasurement,SpectralBeamCalibrationMeasurement,FitSpectralBeamCalibration
from compute.beams import Beam


class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainInterface, self).__init__()
        project_folder = Path(__file__).parent.resolve()
        uic.loadUi(Path(project_folder,r'GUI/main_GUI.ui'), self)

        # fancy name
        self.setWindowTitle('COLBERTo')

        # set devices dict
        self.devices = defaultdict(dict)

        # initialize cryostat
        """ This is a demo devices that has read and write parameters. 
        Illustrates use of parameters"""
        # always try to include communication on important events.
        # This is extremely useful for debugging and troubleshooting.
        print('WARNING you are using a DEMO version of the cryostat')
        self.cryostat = CryoDemo() # launch cryostat interface
        self.devices['cryostat'] = self.cryostat # store in global device dict.

        # initialize Spectrometer
        self.spectrometer = SpectrometerDemo()
        self.spec_length = self.spectrometer.spec_length
        self.devices['spectrometer'] = self.spectrometer
        print('Spectrometer connection failed, use DEMO')

        # Initialize SLM
        self.SLM= SLMDemo()
        self.devices['SLM'] = self.SLM
        print('SLM connection failed, use DEMO')

        # initialize MonochromDemo
        self.Monochrom = MonochromDemo() 
        self.devices['Monochrom'] = self.Monochrom 
        print('Monochrom DEMO connected')

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
        # Spatial calibration tab
        ## Vertical calibration tab
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
        self.fit_snr_spinbox=self.findChild(QtWidgets.QSpinBox,'min_snr_spin_box')
        self.polynomial_order_spinbox=self.findChild(QtWidgets.QSpinBox,'polynomial_order_spin_box')
        self.fit_spectral_calibration_runButton = self.findChild(QtWidgets.QPushButton, 'fit_spectral_calibration')
        self.spectral_calibration_fit_plot_layout=self.findChild(pg.PlotWidget,'spectral_calib_fit_plot_layout')
        self.spectral_calibration_fit_residual_plot_layout=self.findChild(pg.PlotWidget,'spectral_calib_fit_residual_plot_layout')
        self.assign_spectral_calibration_button = self.findChild(QtWidgets.QPushButton, 'assign_spectral_calibraion_button')


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
        self.SpectralCalibrationFitPlot= SpectralCalibFitPlot(self.spectral_calibration_fit_plot_layout)

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
        self.DataHandling = DataHandling(self.parameter, self.spec_length)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        self.DataHandling.sendSpectrum.connect(self.SpectrometerPlot.set_data)
        self.DataHandling.sendMaximum.connect(self.SpectrometerPlot.update_datareader)

        # start Updater to update device read parameters
        self.Updater = UpdateWorker(self.devices, self.readonly_parameter)
        self.Updater.new_parameter.connect(self.update_read_parameter)
        self.Updater.start()

        # set variables
        self.measurement_busy = False
        self.save_folder_path = r'C:/Data/test'
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
        print('I am testing')

    def set_progress(self, progress):
        # set progress bar and define whether a measurement is running. When progess ne 100, no new measurement starts
        self.progress_bar.setValue(int(progress))
        if progress == 100.:
            self.measurement_busy = False

    def change_folder(self):
        # select folder to save data
        self.save_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select data saving folder')
        print('Data folder: ' + str(self.save_folder_path))
        self.change_filename()

    def change_filename(self):
        # change filename to string of LineEdit
        self.filename = str(self.save_folder_path) + "/" + str(self.filename_edit.text().strip('\n'))
        print('filename changed to: ' + str(self.filename))

    def save_data(self):
        # save data
        self.DataHandling.save_data(self.filename, self.comments_edit.toPlainText())

    def load_bg(self):
        # open background file and set as background
        BackgroundFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        bg_path = BackgroundFile[0]
        bg = np.loadtxt(bg_path, delimiter=',')
        self.DataHandling.background = bg[-self.spec_length:, 1]
        # print(np.shape(bg[1:,1]))

        # display background filename
        idx = bg_path.rfind('/')
        self.bg_file_indicator.setText(bg_path[idx+1:])

    def update_check_bg(self):
        self.DataHandling.correct_background = self.bg_check_box.isChecked()
    
    ##### Measurements #####

    def acquire_measurement(self):
        # take one spectrum with spectrometer
        if self.measurement_busy:
            try:
                self.measurement.take_spectrum()
            except AttributeError:
                print('Measurement not started, devices are busy')
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
            print('Measurement not started, devices are busy')

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
            print('Measurement not started, devices are busy')

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
            print('Measurement not started, devices are busy')

    def verticalBeamCalibrationMeasurement(self):
        '''
             Sets up and starts a vertical Beam Calibration.
        ''' 
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement= VerticalBeamCalibrationMeasurement(self.devices,self.grating_period_edit.value(),self.row_increment.value())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.send_intensities.connect(self.VerticalCalibPlot.set_data)
            self.measurement.send_vertical_calibration_data.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def spectralBeamCalibrationMeasurement(self):
        '''
             Sets up and starts a spectral Beam Calibration.
        ''' 
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement= SpectralBeamCalibrationMeasurement(self.devices,self.grating_period_edit.value(),self.column_increment_spinbox.value(),self.column_width_spinbox.value())
            self.spectralfitting=FitSpectralBeamCalibration()
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.send_intensities.connect(self.SpectralCalibDataPlot.set_data)
            self.measurement.send_intensities.connect(self.spectralfitting.extractMaxima)
            self.spectralfitting.send_maxima.connect(self.SpectralCalibrationFitPlot.set_data)
            self.measurement.send_spectral_calibration_data.connect(self.DataHandling.add_calibration)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')
    
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
                beam=Beam(self.SLM.get_width(),self.SLM.get_height())
                beam.set_beamVerticalDelimiters([top_index,bottom_index])
                beam.set_gratingAmplitude(self.grating_period_edit.value())
                self.DataHandling.set_beam((label,beam))

    def stop_measurement(self):
        # stop measurement
        self.measurement.stop()
        self.measurement_busy = False


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
