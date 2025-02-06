"""
Main Data Handling script. Should receive Data from Measurement and/or Hardware Interface classes. Used to order,
arrange and store data. Saves Data in a temp file during data acquirement to prevent memory storage to crash.
Sends Data to Data and Live Viewers.
"""
import time
from PyQt5 import QtCore, QtWidgets
import h5py
import numpy as np
import os.path
import pandas as pd
from collections import deque
import shutil
"""TO DOs: 
implement proper communication between measurements and DataHandling
"""


class DataHandling(QtCore.QThread):

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendMaximum = QtCore.pyqtSignal(np.ndarray)
    sendParameterarray = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, parameter, speclength):
        super(DataHandling, self).__init__()
        self.parameter = parameter
        self.starttime = time.time()

        # initialize Data arrays
        self.speclength = speclength
        self.parameter_queue = {} # initialize FIFO queues for parameter storage
        self.parameter_queue['time'] = deque(maxlen=100000)
        self.parameter_queue['absolute_time'] = deque(maxlen=100000)
        for param in self.parameter:
            self.parameter_queue[param] = deque(maxlen=100000)
        self.param_from_deque = np.zeros([len(self.parameter) + 2, 1])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])
        self.iteration_idx = -1
        self.spec = np.empty([self.speclength, 0])
        self.background = np.empty([self.speclength, 1])
        self.transmission = np.empty([self.speclength, 1])
        self.wavelength = np.empty([self.speclength, 1])
        self.maximum = np.zeros([3])
        self.transmission_option = 'no_corr'
        self.temperature_measured = False
        self.correct_background = False
        self.send_x_idx = 'time'
        self.send_y_idx = 'absolute_time'

        # initialize parameter array
        self.parameter_matrix_full = False
        self.data_in_flash = 0
        self.firstbuffer = True
        self.temp_filename = r"C:\Data\temp.h5"
        self.filename = 'test'

        # initialize Calibration dict
        self.calibration = {}

    #def run(self):
    #    while not self.terminate:
    #        time.sleep(1)
    #    return

    # main update device parameter function
    def update_parameter(self, parameter):
        self.parameter_queue['time'].append(time.time() - self.starttime)
        self.parameter_queue['absolute_time'].append(time.time())
        for idx, param in enumerate(self.parameter):
            self.parameter_queue[param].append(parameter[idx])
        self.sendParameterarray.emit(np.array(self.parameter_queue[self.send_x_idx]), np.array(self.parameter_queue[self.send_y_idx]))
        if self.iteration_idx > 100 - 2:  # 500000
            self.iteration_idx = 0
            #self.parameter_matrix = np.empty([len(parameter) + 1, 500000])
            self.parameter_matrix_full = True

    def clear_data(self):
        self.starttime = time.time()
        self.spec = np.empty([self.speclength, 0])
        self.firstbuffer = 1
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])
        try:
            os.remove(self.temp_filename)
        except:
            pass

    def concatenate_data(self, wls, spec):
        # add data to data array, not used for now
        curr_time = time.time() - self.starttime
        self.wls = wls
        self.spec = np.c_[self.spec, spec]
        for idx, param in enumerate(self.parameter_queue.keys()):
            self.param_from_deque[idx] = self.parameter_queue[param][-1]
        self.parameter_measured = np.c_[self.parameter_measured, self.param_from_deque]
        self.parameter_measured[0, -1] = curr_time
        self.parameter_measured[1, -1] = time.time()
        self.maximum[1] = np.amax(spec)
        self.maximum[2] = wls[np.argmax(spec)]
        self.maximum[0] = curr_time
        self.sendMaximum.emit(self.maximum)
        self.sendSpectrum.emit(wls, spec)
        # to prevent memory overload, save to temp file every 100th spectrum
        self.data_in_flash =self.data_in_flash + 1
        if self.data_in_flash > 99:
            self.save_buffer()
            self.data_in_flash = 0

    # function to receive temperature from measurement script
    def concatenate_temperature(self, temperature):
        pass

    # save data to temp file and clear data in memory
    def save_buffer(self):
        # check for first buffer saving to initialize data array
        if self.firstbuffer:
            spectrum = np.delete(self.spec, 0, 1)
            spectrum_w_param = np.vstack([self.parameter_measured, self.spec])
            print(np.shape(spectrum_w_param))
            with h5py.File(self.temp_filename, 'w') as hf:
                hf.create_dataset("spectra", data=spectrum_w_param, compression="gzip", chunks=True, maxshape=(np.shape(spectrum_w_param)[0],None))
            print('First buffer saved')
            self.firstbuffer = False
        else:
            spectrum = np.delete(self.spec, 0, 1)
            spectrum_w_param = np.vstack([self.parameter_measured, self.spec])
            with h5py.File(self.temp_filename, 'a') as hf:
                hf["spectra"].resize((hf["spectra"].shape[1] + spectrum_w_param.shape[1]), axis=1)
                hf["spectra"][:,-spectrum_w_param.shape[1]:] = spectrum_w_param

        # clear arrays in memory
        self.spec = np.empty([self.speclength, 0])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])

    def save_parameter(self, filename):
        save_length = len(self.parameter_queue['time'])
        save_array = np.empty((len(self.parameter_queue), save_length))
        for idx, param in enumerate(self.parameter_queue.keys()):
            save_array[idx, :] = np.array(self.parameter_queue[param])[0:save_length]
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        with h5py.File( filename + '_' + timestamp + '_parameters.h5', 'w') as hf:
            hf.create_dataset("Parameter", data=save_array, compression="gzip", chunks=True)
        np.savetxt(filename, save_array)
        print('Parameter saved as: ' + filename)

    @QtCore.pyqtSlot(str, str)
    def save_data(self, filename, comments):
        self.save_buffer()
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        shutil.copyfile(self.temp_filename, filename + '_' + timestamp + '.h5')
        self.save_parameter(filename)
        #self.save_worker_thread = SaveWorker(filename, comments, self.parameter, self.spectrumlength, self.temp_filename)
        #self.save_worker_thread.start()
        print('thread started')

    @QtCore.pyqtSlot
    def add_calibration(self,calibration):
        # each calibration should consist of a tuple of name and content
        calibration_name, calibration_value = calibration
        self.calibration[calibration_name] = calibration_value

    def change_send_idx(self, x_idx, y_idx):
        self.send_x_idx = list(self.parameter_queue)[x_idx]
        self.send_y_idx = list(self.parameter_queue)[y_idx]

    def overwrite_popup(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText("Data File already exists. Overwrite?")
        msgBox.setWindowTitle("Warning")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        returnValue = msgBox.exec()
        if returnValue == QtWidgets.QMessageBox.Ok:
            print('Yes, Overwrite!')
            return True
        else:
            print('Cancel')
            return False

    def load_data(self):
        pass

class SaveWorker(QtCore.QThread):

    def __init__(self, filename, comments, parameter, spectrumlength, temp_filename):
        super(SaveWorker, self).__init__()
        self.filename = filename
        self.comments = comments
        self.parameter = parameter
        self.spectrumlength = spectrumlength
        self.temp_filename = temp_filename
        print('SAVE started')

    def run(self):
        # get time for timestamp
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        from_file = self.temp_filename

        # save comments
        comments_file = self.filename + '_metadata_' + timestamp + '.dat'
        with open(comments_file, 'w') as file:
            file.write(self.comments)
            file.write('\n \n \n###### Measurement parameters ###### \n')
            for param in self.parameter.keys():
                file.write(param + ': ' + str(self.parameter[param]) + '\n')

        # transpose data from temp file to final file. Saving in rows is faster than in columns
        # convert CSV with rows to columns using batches (required for large files)
        NCOLS = self.spectrumlength[0]  # The exact number of columns
        batch_size = 50
        to_file = self.filename + '_' + timestamp + '.csv'
        for batch in range(NCOLS // batch_size + bool(NCOLS % batch_size)):
            lcol = batch * batch_size
            rcol = min(NCOLS, lcol + batch_size)
            data = pd.read_csv(from_file, usecols=range(lcol, rcol), header=None)
            with open(to_file, 'a') as _f:
                data.T.to_csv(_f, header=None, index=None, line_terminator='\n')
        print('Data saved as: ' + to_file)
        return