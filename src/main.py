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
import pyqtgraph as pg
from functools import partial
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from GUI.LUT_Calib_plot import LUT_Calib_plot
from drivers.CryoDemo import CryoDemo
from drivers.SpectrometerDemo_advanced import SpectrometerDemo
from drivers.SLM import Slm
from drivers.SLMDemo import SLMDemo
from drivers.StresingDemo import StresingDemo
from drivers.MonochromDemo import MonochromDemo
from DataHandling.DataHandling import DataHandling
from measurements.MeasurementClasses import AcquireMeasurement,RunMeasurement,BackgroundMeasurement, \
    ViewMeasurement
import logging
import datetime

from measurements.Calibration_Classes import Measure_LUT_PhasetoGreyscale,Generate_LUT_PhasetoGreyscale

logger = logging.getLogger(__name__)
class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainInterface, self).__init__()
        project_folder = Path(__file__).parent.resolve()
        uic.loadUi(Path(project_folder,r'GUI/main_GUI.ui'), self)
        logging.basicConfig(filename='main.log', level=logging.INFO)
        logger.info('%s Started log'%datetime.datetime.now())
        # fancy name
        self.setWindowTitle('COLBERTo')

        # set devices dict
        self.devices = defaultdict(dict)

        # initialize cryostat
        """ This is a demo devices that has read and write parameters. 
        Illustrates use of parameters"""
        # always try to include communication on important events.
        # This is extremely useful for debugging and troubleshooting.
        logger.warning('%s You are using a DEMO version of the cryostat'%datetime.datetime.now())
        self.cryostat = CryoDemo() # launch cryostat interface
        self.devices['cryostat'] = self.cryostat # store in global device dict.

        try:
            from drivers.OceanSpectrometer import OceanSpectrometer
            self.spectrometer = OceanSpectrometer()
            self.spectrometer.start()
            self.spec_length = self.spectrometer.spec_length
            self.devices['spectrometer'] = self.spectrometer
            logger.warning('%s Spectrometer Connected' % datetime.datetime.now())
        except:
            self.spectrometer = SpectrometerDemo()
            self.spec_length = self.spectrometer.spec_length
            self.devices['spectrometer'] = self.spectrometer
            logger.warning('%s Spectrometer connection failed, use DEMO' % datetime.datetime.now())

        # initialize SLM
        try:
            self.SLM = Slm()
            self.devices['SLM'] = self.SLM
            #print('SLM Connected')
            logger.info('%s SLM connected' % datetime.datetime.now())
        except:
            self.SLM = SLMDemo()
            self.devices['SLM'] = self.SLM
            logger.info('%s SLMDemo connected'%datetime.datetime.now())

        # initialize StresingDemo
        self.Stresing = StresingDemo()
        self.devices['Stresing'] = self.Stresing
        logger.info('%s Stresing connected'%datetime.datetime.now())

        # initialize MonochromDemo
        self.Monochrom = MonochromDemo() 
        self.devices['Monochrom'] = self.Monochrom 
        logger.info('%s Monochrom DEMO connected'%datetime.datetime.now())

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
        self.kinetic_lineEdit = self.findChild(QtWidgets.QLineEdit, 'kinetic_lineEdit')
        self.kinetic_run_button = self.findChild(QtWidgets.QPushButton, 'kinetic_run_pushButton')
        self.SLM_tab = self.findChild(QtWidgets.QWidget, 'SLM_tab')
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

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.SLM)
        self.SLM_tab.setLayout(vbox)
        self.LUT_Calib_plot = LUT_Calib_plot(self.LUT_calib_plot_layout)

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
        self.kinetic_lineEdit.editingFinished.connect(self.change_kinetic_interval)
        self.kinetic_run_button.clicked.connect(self.kinetic_measurement)
        # LUT Calibration Measurement Connect Events
        self.measure_LUT_calib_button.clicked.connect(self.Measure_LUT_PhasetoGreyscale)  # measure spectrum
        self.select_LUT_Data_file_button.clicked.connect(self.load_LUT_Data_file)  # select spectrum data file
        self.generate_LUT_calib_button.clicked.connect(
            self.Generate_LUT_PhasetoGreyscale)  # use spectrum data to generate LUT file

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
            logger.info('%s Measurement not started, devices are busy'%datetime.datetime.now())

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
