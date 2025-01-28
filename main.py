# -*- coding: utf-8 -*-
"""
Created on Thu Sep  1 14:13:11 2022
@author: David Tiede
"""

import sys
import time
import re
import os
from collections import defaultdict
import numpy as np
from usb.core import USBTimeoutError
from PyQt5 import QtCore, QtWidgets, uic
from functools import partial
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from GUI.DataPlot import DataPlot
from Hardware.CryocoreDemo import CryocoreDemo
from Hardware.CryoMercury import CryoMercury
from Hardware.OceanSpectrometer import OceanSpectrometer
from Hardware.SpectrometerDemo import SpectrometerDemo
#from Hardware.ThorlabsShutter import ThorlabsShutter
#from Hardware.ThorlabsShutterDemo import ThorlabsShutterDemo
from Hardware.Orpheus import Orpheus
from Hardware.OrpheusDemo import OrpheusDemo
from Hardware.OphirJuno import OphirJuno
from Hardware.OphirJunoDemo import OphirJunoDemo
from Hardware.Arduino import Arduino
from Hardware.ArduinoDemo import ArduinoDemo
#from Hardware.ThorlabsFW import ThorlabsFW
from Hardware.ThorlabsFWDemo import ThorlabsFWDemo
#from Hardware.UFClient import UFClient
from DataHandling.DataHandling import DataHandling
from seabreeze.cseabreeze._wrapper import SeaBreezeError
from Measurements.MeasurementClasses import AcquireMeasurement, RunMeasurement, TSeriesMeasurement, \
    BackgroundMeasurement, ViewMeasurement, TwoPhotonMeasurement, KineticMeasurement, SetPowerMeasurement, \
    PPSeriesMeasurement
import subprocess


class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainInterface, self).__init__()
        project_folder = os.getcwd()
        uic.loadUi(project_folder + r'\GUI\main_GUI.ui', self)

        # fancy name
        self.setWindowTitle('MOMpy')

        # set devices dict
        self.devices = defaultdict(dict)

        # initialize cryostat
        try:
            self.cryostat = CryoMercury('ASRL10::INSTR')
            self.devices['cryostat'] = self.cryostat
            self.cryostat.start()
            print('Mercury Cryostat connected')
        except:
            print('Initialization of cryostat failed')
            self.cryostat = CryocoreDemo()
            self.devices['cryostat'] = self.cryostat

        # initialize Spectrometer
        try:
            self.spectrometer = OceanSpectrometer()
            self.spectrometer.start()
            self.speclength = self.spectrometer.speclength
            self.devices['spectrometer'] = self.spectrometer
        #except: #USBTimeoutError or SeaBreezeError: #<== Error Handling to be improved.
        except Exception as e:
            #Print the type of exception
            print(f"An error occurred: {e}")
            print(f"Type of error: {type(e)}")
            print('Use Demo Spectrometer')
            self.spectrometer = SpectrometerDemo()
            self.speclength = self.spectrometer.speclength
            self.devices['spectrometer'] = self.spectrometer
            print('Spectrometer connection failed, try to reset')
            #subprocess.run(
            #    [r'C:\Program Files (x86)\Windows Kits\10\Tools\10.0.22621.0\x64\devcon.exe', 'restart',
            #     r'USB\VID_2457&PID_1022\6&1E267330&0&1'])
            #time.sleep((5))
            #try:
            #    self.spectrometer = OceanSpectrometer()
            #    self.spectrometer.start()
            #    self.speclength = self.spectrometer.speclength
            #    self.devices['spectrometer'] = self.spectrometer
            #except USBTimeoutError:

        # initialize Orpheus
        try:
            self.orpheus = Orpheus()
            if self.orpheus.match is None:
                self.orpheus = OrpheusDemo()
                print('Orpheus not connected')
            else:
                self.devices['orpheus'] = self.orpheus
                self.orpheus.start()
                print('Orpheus connected')
        except:
            print('Orpheus not connected')
            #self.orpheus = OrpheusDemo()
            #self.devices['orpheus'] = self.orpheus

        # initialize Powermeter
        try:
            self.powermeter = OphirJuno()
            self.powermeter.start()
            self.devices['powermeter'] = self.powermeter
        except:
            self.powermeter = OphirJunoDemo()
            self.devices['powermeter'] = self.powermeter
            print('Powermeter not connected')

        # initialize arduino
        # self.arduino = Arduino('COM3')
        try:
            self.arduino = Arduino('COM3')
            self.arduino.start()
            self.devices['arduino_shutters'] = self.arduino
            print('Arduino shutters connected')
        except:
            self.arduino = ArduinoDemo()
            self.devices['arduino_shutters'] = self.arduino
            print('Arduino shutters not connected')

        # initialize Thorlabs FW
        #self.thorlabs_FW = ThorlabsFW('COM9')
        try:
            #self.thorlabs_FW = ThorlabsFW('COM7')
            self.thorlabs_FW = ThorlabsFW('COM6')
            self.thorlabs_FW.start()
            self.devices['thorlabs_fw'] = self.thorlabs_FW
            print('Thorlabs FW connected')
        except:
            self.thorlabs_FW = ThorlabsFWDemo('COM6')
            self.thorlabs_FW.start()
            self.devices['thorlabs_fw'] = self.thorlabs_FW
            print('Thorlabs FW not connected, Demo is used')

        # initialize Thorlabs Shutter
        #try:
        #    self.thorlabs_shutter = ThorlabsShutter()
        #    self.thorlabs_shutter.start()
        #    self.devices['thorlabs_shutter'] = self.thorlabs_shutter
        #    print('Thorlabs Shutter connected')
        #except:
        print('Thorlabs Shutter not connected')

        # initialize UF Client (HELIOS)
        #self.UF_client = UFClient()
        #self.devices['uf_client'] = self.UF_client

        # find items to complement in GUI
        self.parameter_tree = self.findChild(QtWidgets.QTreeWidget, 'parameters_treeWidget')
        self.data_tab = self.findChild(QtWidgets.QWidget, 'data_tab')
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
        self.Tseries_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_lineEdit')
        self.Tseries_stab_time_box = self.findChild(QtWidgets.QSpinBox, 'Tseries_stab_time_spinBox')
        self.Tseries_run_button = self.findChild(QtWidgets.QPushButton, 'Tseries_run_pushButton')
        self.Tseries_ref_power_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_ref_power_doubleSpinBox')
        self.Tseries_int_time_WL_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_int_time_WL_doubleSpinBox')
        self.Tseries_int_time_orpheus_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_int_time_orpheus_doubleSpinBox')
        self.Tseries_power_dep_checkBox = self.findChild(QtWidgets.QCheckBox, 'Tseries_power_dep_checkBox')
        self.Tseries_two_sources_checkBox = self.findChild(QtWidgets.QCheckBox, 'Tseries_two_sources_checkBox')
        self.Tseries_spectra_avg_box = self.findChild(QtWidgets.QSpinBox, 'Tseries_spectra_avg_spinBox')
        self.Tseries_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_lineEdit')
        self.Tseries_int_time_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_int_time_lineEdit')
        self.Tseries_filter_pos_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_filter_pos_lineEdit')
        self.bg_button = self.findChild(QtWidgets.QPushButton, 'Acquire_bg_pushButton')
        self.bg_check_box = self.findChild(QtWidgets.QCheckBox, 'bg_checkBox')
        self.bg_file_indicator = self.findChild(QtWidgets.QLineEdit, 'bg_file_lineEdit')
        self.bg_scans_box = self.findChild(QtWidgets.QSpinBox, 'bg_scans_spinBox')
        self.bg_select_box = self.findChild(QtWidgets.QPushButton, 'select_bg_pushButton')
        self.TPE_run_button = self.findChild(QtWidgets.QPushButton, 'TPE_run_pushButton')
        self.ref_power_box = self.findChild(QtWidgets.QDoubleSpinBox, 'ref_power_doubleSpinBox')
        self.ref_wave_box = self.findChild(QtWidgets.QSpinBox, 'ref_wave_spinBox')
        self.TPE_series_lineEdit = self.findChild(QtWidgets.QLineEdit, 'TPE_series_lineEdit')
        self.TPE_spectra_number_box = self.findChild(QtWidgets.QSpinBox, 'TPE_spectra_number_spinBox')
        self.TPE_scan_number_box = self.findChild(QtWidgets.QSpinBox, 'TPE_scan_number_spinBox')
        self.select_power_calib_pushButton = self.findChild(QtWidgets.QPushButton, 'select_power_calib_pushButton')
        self.power_calib_lineEdit = self.findChild(QtWidgets.QLineEdit, 'power_calib_lineEdit')
        self.orpheus_interaction_checkBox = self.findChild(QtWidgets.QCheckBox, 'orpheus_interaction_checkBox')
        self.TPE_skip_power_checkBox = self.findChild(QtWidgets.QCheckBox, 'TPE_skip_power_checkBox')
        self.kinetic_lineEdit = self.findChild(QtWidgets.QLineEdit, 'kinetic_lineEdit')
        self.kinetic_run_button = self.findChild(QtWidgets.QPushButton, 'kinetic_run_pushButton')
        self.kinetic_run_button_2 = self.findChild(QtWidgets.QPushButton, 'kinetic_run_pushButton_2')
        self.transmission_spectrum_action = self.findChild(QtWidgets.QAction, 'actionChoose_reference_spectrum')
        self.transmission_no_corr_action = self.findChild(QtWidgets.QAction, 'actionNo_correction')
        self.transmission_transmission_action = self.findChild(QtWidgets.QAction, 'actionTransmission')
        self.transmission_absorption_action = self.findChild(QtWidgets.QAction, 'actionAbsorption')
        self.transmission_absorbance_action = self.findChild(QtWidgets.QAction, 'actionAbsorbance')
        set_power_layout = self.findChild(QtWidgets.QHBoxLayout, 'set_power_layout')
        self.PPseries_filter_pos_lineEdit = self.findChild(QtWidgets.QLineEdit, 'PPseries_filter_pos_lineEdit')
        self.PPseries_wait_time_box = self.findChild(QtWidgets.QSpinBox, 'PPseries_wait_time_spinBox')
        self.PPseries_acq_time_box = self.findChild(QtWidgets.QSpinBox, 'PPseries_acq_time_spinBox')
        self.PPseries_run_button = self.findChild(QtWidgets.QPushButton, 'PPseries_run_pushButton')

        # initial parameter values, retrieved from devices
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for device in self.devices.keys():
            self.parameter_dic[device] = self.devices[device].parameter_display_dict

        # create parameter array for easy access
        self.create_parameter_array()

        # add items to GUI
        #self.DataPlot = DataPlot()
        #vbox = QtWidgets.QVBoxLayout()
        #vbox.addWidget(self.DataPlot)
        #self.data_tab.setLayout(vbox)
        #self.DataPlot.start()
        self.SpectrometerPlot = SpectrometerPlot()
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.SpectrometerPlot)
        self.spectro_tab.setLayout(vbox)
        self.ParameterPlot = ParameterPlot(self.parameter_dic)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.ParameterPlot)
        self.parameter_tab.setLayout(vbox)
        # add set power to GUI
        if 'orpheus' in self.devices.keys():
            self.set_power_button = QtWidgets.QPushButton('Set power')
            self.set_power_box = QtWidgets.QDoubleSpinBox()
            self.set_power_coarse_check = QtWidgets.QCheckBox()
            self.set_power_coarse_check.setText('Coarse')
            self.set_power_box.setSuffix(' nW')
            self.set_power_box.setMaximum(1000000000)
            self.set_power_box.setStyleSheet('background-color: rgb(255, 255, 255);')
            self.set_power_button.clicked.connect(self.set_power_measurement)
            set_power_layout.addWidget(self.set_power_button)
            set_power_layout.addWidget(self.set_power_box)
            set_power_layout.addWidget(self.set_power_coarse_check)


        # set parameter tree and fill with spinboxes. Iterate over all parameters defined in hardware classes
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
        self.DataHandling = DataHandling(self.parameter, self.speclength)
        #self.DataHandling.sendTarray.connect(self.CryoPlot.set_data)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        self.DataHandling.sendSpectrum.connect(self.SpectrometerPlot.set_data)
        #self.DataHandling.sendMaximum.connect(self.DataPlot.update_parameterplot)
        self.DataHandling.sendMaximum.connect(self.SpectrometerPlot.update_datareader)

        # start Updater to update device read parameters
        self.Updater = UpdateWorker(self.devices, self.readonly_parameter)
        self.Updater.new_parameter.connect(self.update_read_parameter)
        self.Updater.start()

        # set variables
        self.measurement_busy = False
        self.save_folder_path = r'C:/Data/test'
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
        self.Tseries_lineEdit.editingFinished.connect(self.change_Tseries)
        self.Tseries_run_button.clicked.connect(self.Tseries_measurement)
        self.bg_button.clicked.connect(self.background_measurement)
        self.bg_select_box.clicked.connect(self.load_bg)
        self.bg_check_box.stateChanged.connect(self.update_check_bg)
        self.TPE_run_button.clicked.connect(self.TPE_series_measurement)
        self.TPE_series_lineEdit.editingFinished.connect(self.change_TPE_series)
        self.select_power_calib_pushButton.clicked.connect(self.load_power_calib)
        self.ParameterPlot.send_idx_change.connect(self.DataHandling.change_send_idx)
        self.ParameterPlot.send_parameter_filename.connect(self.DataHandling.save_parameter)
        self.orpheus_interaction_checkBox.stateChanged.connect(self.update_orpheus_interaction)
        self.kinetic_lineEdit.editingFinished.connect(self.change_kinetic_interval)
        self.kinetic_run_button.clicked.connect(self.kinetic_measurement)
        self.kinetic_run_button_2.clicked.connect(self.kinetic_measurement)
        self.transmission_spectrum_action.triggered.connect(self.load_transmission_spectrum)
        self.transmission_no_corr_action.changed.connect(self.change_transmission_options)
        self.transmission_transmission_action.changed.connect(self.change_transmission_options)
        self.transmission_absorption_action.changed.connect(self.change_transmission_options)
        self.transmission_absorbance_action.changed.connect(self.change_transmission_options)
        self.PPseries_run_button.clicked.connect(self.PPseries_measurement)

        # run some functions once to define default values
        self.change_Tseries()
        self.change_TPE_series()
        self.change_filename()

        # show GUI
        self.show()

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

    def change_Tseries(self):
        # generate temperature array for T dep measurement
        try:
            self.Tseries =[]
            txt = self.Tseries_lineEdit.text()
            i = 0
            digits = {}
            for s in re.split(':| ', txt):
                if s.replace(".", "", 1).isdigit():
                    digits[i] = s
                    i = i+1.
            for j in range(int(i/3)):
                self.Tseries = np.append(self.Tseries, np.linspace(float(digits[3*j]), float(digits[3*j+2]), int(digits[3*j+1])))
            print('T series : ' + str(self.Tseries))
        except:
            print('Lecture of T series failed')

    def change_TPE_series(self):
        # generate temperature array for T dep measurement
        try:
            self.TPE_series = []
            txt = self.TPE_series_lineEdit.text()
            i = 0
            digits = {}
            for s in re.split(':| ', txt):
                if s.replace(".", "", 1).isdigit():
                    digits[i] = s
                    i = i + 1.
            for j in range(int(i / 3)):
                self.TPE_series = np.append(self.TPE_series, np.linspace(float(digits[3 * j]), float(digits[3 * j + 2]),
                                                                     int(digits[3 * j + 1])))
            print('TPE series : ' + str(self.TPE_series))
        except:
            print('Lecture of TPE series failed')

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
            print('Kinetic Interval: ' + str(self.kinetic_interval))
        except:
            print('Lecture of kinetic interval failed')

    def load_bg(self):
        # open background file and set as background
        BackgroundFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        bg_path = BackgroundFile[0]
        bg = np.loadtxt(bg_path, delimiter=',')
        self.DataHandling.background = bg[-self.speclength:, 1]
        # print(np.shape(bg[1:,1]))

        # display background filename
        idx = bg_path.rfind('/')
        self.bg_file_indicator.setText(bg_path[idx+1:])

    def load_power_calib(self):
        # open background file and set as background
        power_calib_file_File = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        pc_path = power_calib_file_File[0]
        self.power_calib_array = np.loadtxt(pc_path)
        # print(np.shape(bg[1:,1]))

        # display background filename
        idx = pc_path.rfind('/')
        self.power_calib_lineEdit.setText(pc_path[idx+1:])

    def load_transmission_spectrum(self):
        # open background file and set as background
        transmission_file = QtWidgets.QFileDialog.getOpenFileName(self, 'Select transmission reference data')
        transmission_path = transmission_file[0]
        bg = np.loadtxt(transmission_path, delimiter=',')
        self.DataHandling.transmission = bg[-self.speclength:, 1]
        # print(np.shape(bg[1:,1]))

    def change_transmission_options(self):
        if self.transmission_no_corr_action.isChecked():
            self.DataHandling.transmission_option = 'no_corr'
        elif self.transmission_transmission_action.isChecked():
            self.DataHandling.transmission_option = 'transmission'
        elif self.transmission_absorption_action.isChecked():
            self.DataHandling.transmission_option = 'absorption'
        elif self.transmission_absorbance_action.isChecked():
            self.DataHandling.transmission_option = 'absorbance'

    def update_check_bg(self):
        self.DataHandling.correct_background = self.bg_check_box.isChecked()

    def update_orpheus_interaction(self):
        self.orpheus.ignore_user_actions = self.orpheus_interaction_checkBox.isChecked()

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
            # self.measurement.sendPreview.connect(self.SpectrometerPlot.set_data_preview)
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

    def Tseries_measurement(self):
        # take temperature dependent measurements as defined in automation GUI section
        if not self.measurement_busy:
            print('Start T-Dependent Measurement ')
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = TSeriesMeasurement(self.devices, self.parameter, self.Tseries,
                                                  self.Tseries_stab_time_box.value(),self.Tseries_two_sources_checkBox.isChecked(),
                                                  self.Tseries_ref_power_box.value(),self.Tseries_int_time_WL_box.value(),
                                                  self.Tseries_int_time_orpheus_box.value(),
                                                  self.Tseries_spectra_avg_box.value(),
                                                  self.Tseries_power_dep_checkBox.isChecked(),
                                                  self.Tseries_filter_pos_lineEdit.text(),
                                                  self.Tseries_int_time_lineEdit.text())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendTemperature.connect(self.DataHandling.concatenate_temperature)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()

    def TPE_series_measurement(self):
        # take two photon excitation measurements as defined in automation GUI section
        if not self.measurement_busy:
            print('Start TPE Measurement ')
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = TwoPhotonMeasurement(self.devices, self.parameter, self.TPE_series,
                                                    self.ref_wave_box.value(), self.ref_power_box.value(),
                                                    self.TPE_spectra_number_box.value(),self.TPE_scan_number_box.value(),
                                                    self.TPE_skip_power_checkBox.isChecked(),self.power_calib_array)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def kinetic_measurement(self):
        # take time resolved measurements as defined in automation GUI section
        if not self.measurement_busy:
            self.measurement_busy = True
            #self.DataPlot.clear_data()
            self.DataHandling.clear_data()
            self.change_kinetic_interval()
            self.measurement =KineticMeasurement(self.devices, self.parameter, self.kinetic_interval)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendParameter.connect(self.change_parameter)
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

    def set_power_measurement(self):
        # acquire background to subtract from spectra. May average over several spectra
        if not self.measurement_busy:
            self.measurement_busy = True
            self.measurement = SetPowerMeasurement(self.devices, self.set_power_box.value(),
                                                   self.set_power_coarse_check.isChecked())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def PPseries_measurement(self):
        # UF PP measurement dependent on different parameters
        if not self.measurement_busy:
            self. measurement_busy = True
            self. measurement = PPSeriesMeasurement(self.devices,self.PPseries_filter_pos_lineEdit.text(),
                                                    self.PPseries_wait_time_box.value(), self.PPseries_acq_time_box.value(),
                                                    self.filename)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')


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