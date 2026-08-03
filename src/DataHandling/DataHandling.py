"""
Main Data Handling script. Should receive Data from Measurement and/or Hardware Interface classes. Used to order,
arrange and store data. Saves Data in a temp file during data acquirement to prevent memory storage to crash.
Sends Data to Data and Live Viewers. It can be handled as an object of measurement classes, such that measurement can
easily interact with predefined storage function. For now, measurements can send spectra and add attributes,
functionalities might have to be extended depending on the exact needs of the measurements.
Although passing through DataHandling when manupilation data is a bit complex, it helps to have hardware parameters
always assigned to the corresponding measurements.
"""
import time
from PyQt5 import QtCore, QtWidgets
import h5py
import numpy as np
import os.path
from collections import deque
import shutil
import threading
import logging
import datetime
from numpy.polynomial import Polynomial as P
"""TO DOs: 
- consider implementing data storage for several data acquiring devices (e.g. 2 spectrometer simultaneously) 
- Implement proper saving of Beam object. Needs to be discussed. 
"""

logger = logging.getLogger(__name__)

class DataHandling(QtCore.QThread):

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendMaximum = QtCore.pyqtSignal(np.ndarray) # not used for now, to be implemented for direct measurement control
    sendParameterarray = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeams = QtCore.pyqtSignal(object)
    bufferSaveSignal = QtCore.pyqtSignal(object, object, object, object)

    def __init__(self, parameter, speclength):
        super(DataHandling, self).__init__()
        self.parameter = parameter
        self.starttime = time.time()

        # initialize data arrays, their uses are explained in the corresponding functions
        self.speclength = speclength
        self.data_dim = np.size(speclength) #dimension of data
        self.parameter_queue = {} # initialize FIFO queues for parameter storage
        self.parameter_queue['time'] = deque(maxlen=100000)
        self.parameter_queue['absolute_time'] = deque(maxlen=100000)
        for param in self.parameter:
            self.parameter_queue[param] = deque(maxlen=100000)
        self.param_from_deque = np.zeros([len(self.parameter) + 2, 1])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])

        # preallocate data arrays depending on data dimension (1D or 2D).
        """ The background is zeroed, not np.empty: an np.empty array holds whatever was in memory,
        and subtracting it corrupts every spectrum silently. has_background says whether a real
        background was ever measured or loaded; until then correct_background subtracts nothing. """
        if self.data_dim  == 1:
            self.spec = np.empty([self.speclength, 0])
            self.background = np.zeros([self.speclength, 1])
            self.wls = np.empty([self.speclength, 1])
        else:
            self.spec = np.empty([0,self.speclength[0],self.speclength[1]])
            self.background = np.zeros([1,self.speclength[0],self.speclength[1]])
            self.wls = np.empty([self.speclength[1], 1])
        self.has_background = False
        self.background_warned = False

        # set initial values
        self.maximum = np.zeros([3])
        self.correct_background = False
        self.send_x_idx = 'time'
        self.send_y_idx = 'absolute_time'

        # initialize parameter array
        self.parameter_matrix_full = False
        self.data_in_flash = 0
        self.firstbuffer = True
        self.temp_filename = r"C:\TEMP\temp.h5"
        self.filename = 'test'

        # initialize Calibration dict
        self.calibration = {}

        # initialize BufferWorker
        """ The worker writes the buffer in its own thread. save_data() has to know when that write
        has actually finished before it copies the file, so the worker signals completion through
        this event. It used to sleep 0.5 s and hope. """
        self.buffer_written = threading.Event()
        self.thread = QtCore.QThread()
        self.BufferWorker = BufferWorker(self.temp_filename, self.data_dim, self.buffer_written)
        self.BufferWorker.moveToThread(self.thread)
        self.thread.start()
        self.bufferSaveSignal.connect(self.BufferWorker.save_buffer)
        # initialize beams dict
        self.beams={}

    # main update device parameter function
    def update_parameter(self, parameter):
        """ This is an important part of hardware parameter control. We use "deque" as efficient First-In-First-Out
        Queues that allow to have a continuous acces to the last 100.000 hardware parameters. Each parameter has their
        on deque object. Each time the update parameter function is called by the updater, the most updated value of the
        hardware parameter is added to the deque.
            input:
                - parameter (dict): parameter name -> current value. Names absent from the dictionary,
                  and values that are not numbers such as the cryostat reporting "Stable", repeat the
                  last recorded value so the columns stay aligned with the spectra.

        This used to take a sequence indexed positionally, and nothing in the code ever called it.
        The queues therefore stayed empty, which left parameter_measured full of zeros: no hardware
        setting was ever stored beside the data it belongs to.
        """
        self.parameter_queue['time'].append(time.time() - self.starttime)
        self.parameter_queue['absolute_time'].append(time.time())

        for param in self.parameter:
            queue = self.parameter_queue[param]
            try:
                value = float(parameter[param])
            except (KeyError, TypeError, ValueError):
                value = queue[-1] if queue else 0.0
            queue.append(value)

        self.sendParameterarray.emit(np.array(self.parameter_queue[self.send_x_idx]), np.array(self.parameter_queue[self.send_y_idx]))

    def clear_data(self):
        """Each time a new measurement is started, DataHandling is reset."""
        self.starttime = time.time()

        if self.data_dim == 1: # clear data arrays depending on dimension
            self.spec = np.empty([self.speclength, 0])
        else:
            self.spec = np.empty([1,self.speclength[0],self.speclength[1]])
        self.BufferWorker.firstbuffer = True
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])
        try:
            os.remove(self.temp_filename)
        except:
            pass

    def concatenate_data(self, wls, spec):
        """ This function concatenates all received spectra. it keeps the last 100 spectra directly accessible. If
        more than 100 spectra are acquired, they are buffersaved in a .h5 file, to prevent memory overload and allow
        acquisiton of infinite spectra. """
        # add data to data array, not used for now
        curr_time = time.time() - self.starttime
        self.wls = wls
        if self.data_dim == 1:
            if self.correct_background:
                spec = self.subtract_background(spec)
            self.spec = np.c_[self.spec, spec]

        else:
            self.spec = np.concatenate([self.spec, spec[np.newaxis, ...]])
        """ A parameter only has a recorded value once update_parameter() has run for it. Reading
        queue[-1] unconditionally raised IndexError on every spectrum, which killed this slot before
        sendSpectrum was emitted: the measurement finished, the traceback went to stderr rather than
        to the log, and no spectrum ever reached the plot. Parameters with nothing recorded keep
        their previous value instead. """
        for idx, param in enumerate(self.parameter_queue.keys()):
            queue = self.parameter_queue[param]
            if queue:
                self.param_from_deque[idx] = queue[-1]
        self.parameter_measured = np.c_[self.parameter_measured, self.param_from_deque]
        self.parameter_measured[0, -1] = curr_time
        self.parameter_measured[1, -1] = time.time()
        self.sendSpectrum.emit(wls, spec)
        # to prevent memory overload, save to temp file every 100th spectrum
        self.data_in_flash = self.data_in_flash + 1
        if self.data_in_flash > 49:
            self.save_buffer()
            self.data_in_flash = 0

        # Extract maxima of data to display them in SpectrumViewer
        self.maximum[1] = np.amax(spec)
        if self.data_dim == 1:
            self.maximum[2] = wls[np.argmax(spec)]
        else:
            self.maximum[2] = wls[np.unravel_index(spec.argmax(), spec.shape)[1]]
        self.maximum[0] = curr_time
        self.sendMaximum.emit(self.maximum)

    def subtract_background(self, spec):
        """
            Subtracts the stored background, and refuses to do anything else.
            Returns the spectrum unchanged, with one warning, when no background has been measured or
            loaded, or when the stored one does not match the current spectrum length. Both used to go
            through unnoticed: the background array was allocated with np.empty and no measurement ever
            filled it, so ticking background correction subtracted uninitialised memory.
            input:
                - spec (np.ndarray): spectrum to correct
            output:
                - np.ndarray: corrected spectrum, or the original one if no valid background
        """
        reason = None
        if not self.has_background:
            reason = 'no background has been acquired or loaded'
        elif self.background.size != np.size(spec):
            reason = ('background is %d points, spectrum is %d'
                      % (self.background.size, np.size(spec)))
        if reason is not None:
            if not self.background_warned:
                logger.warning('%s Background correction is on but was not applied: %s'
                               % (datetime.datetime.now(), reason))
                self.background_warned = True
            return spec
        return spec - self.background.ravel()

    def use_background(self, spec):
        """
            Adopts a spectrum as the background to subtract.
            input:
                - spec (np.ndarray): background spectrum. A file holding several spectra is accepted,
                  in which case the last one is used, matching how load_bg used to slice it.
            output:
                - bool: whether a usable background was stored
        """
        flat = np.asarray(spec, dtype=float).ravel()
        if self.data_dim == 1 and flat.size != self.speclength:
            if self.speclength and flat.size % self.speclength == 0:
                flat = flat[-self.speclength:]
            else:
                logger.error('%s Background rejected: %d points for a %s point spectrum'
                             % (datetime.datetime.now(), flat.size, self.speclength))
                return False
        self.background = flat.reshape(-1, 1) if self.data_dim == 1 else np.asarray(spec, dtype=float)
        self.has_background = True
        self.background_warned = False
        logger.info('%s Background stored (%d points)' % (datetime.datetime.now(), flat.size))
        return True

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_background(self, wls, spec):
        """
            Slot for a background measurement, which emits wavelengths and intensities together.
            input:
                - wls (np.ndarray): wavelengths, unused
                - spec (np.ndarray): measured background
        """
        self.use_background(spec)

    # save data to temp file and clear data in memory
    def save_buffer(self):
        """ Saves data to a temporary file and populates it each time more than 100 spectra have been acquired.
        If the file is created, some attributes such as yaxis and parameter keys are added."""
        t1 = time.time()
        self.buffer_written.clear()
        self.bufferSaveSignal.emit(self.spec, self.wls, self.parameter_queue, self.parameter_measured)

        # clear arrays in memory
        if self.data_dim == 1:
            self.spec = np.empty([self.speclength, 0])
        else:
            self.spec = np.empty([0,self.speclength[0],self.speclength[1]])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])


    def save_parameter(self, filename):
        """ Saves parameters to an independent .h5 file. We still might want to adapt how this is handled."""
        save_length = len(self.parameter_queue['time'])
        save_array = np.empty((len(self.parameter_queue), save_length))
        for idx, param in enumerate(self.parameter_queue.keys()):
            save_array[idx, :] = np.array(self.parameter_queue[param])[0:save_length]
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        with h5py.File( filename + '_' + timestamp + '_parameters.h5', 'w') as hf:
            hf.create_dataset("parameter", data=save_array, compression="gzip", chunks=True)
            hf['parameter'].attrs["parameter_keys"] = list(self.parameter_queue.keys())
        np.savetxt(filename, save_array)
        logger.info('%s Parameter saved as: ' % datetime.datetime.now() + filename)

    @QtCore.pyqtSlot(str, str)
    def save_data(self, filename, comments):
        """saves data. Each time data is saved, parameters are saved aswell. """
        self.save_buffer()
        """ Wait for the worker to finish writing rather than sleeping a fixed 0.5 s: on a large
        buffer or a slow disk that sleep expired first and the file below was copied half written.
        The timeout is long because it only has to cover a genuinely slow write. """
        if not self.buffer_written.wait(timeout=60):
            logger.error('%s Not saved: the buffer was still being written after 60 s'
                         % datetime.datetime.now())
            return
        with h5py.File(self.temp_filename, 'a') as hf:
            hf.attrs["comments"] = comments
            if len(self.calibration) > 0 :
                for k in self.calibration.keys():
                    hf.attrs[k] = self.calibration[k]


        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        savename = filename + '_' + timestamp + '.h5'
        shutil.copyfile(self.temp_filename, savename)
        logger.info('%s Data saved as: ' %datetime.datetime.now() + savename )

    #@QtCore.pyqtSlot
    def add_calibration(self,calibration):
        # to be used from calibration scripts. Each calibration should consist of a tuple of name and content
        calibration_name, calibration_value = calibration
        self.calibration[calibration_name] = calibration_value

    def set_beam(self, name_and_beam):
        '''
            Adds or updates the beam at the provided index
            input:
                - tuple: (name,Beam) First argument of tuple is beam name and second is Beam object to set
        '''
        beam_name, beam = name_and_beam
        self.beams[beam_name] = beam
        self.get_beams() # Emits the beams as soon as they are changed

    def set_multiple_beams(self,beamDict):
        """
            Updates multiple beams at once using a dictionnary of beams
            input:
                - beamDict: Dictionnary of Beam objects
        """
        for items in beamDict.items():
            beam_name,beam=items
            self.beams[beam_name]=beam
        self.get_beams() # Emits the beams as soon as they are changed

    def get_beams(self):
        '''
            Triggers emission of beams to connected slots when called
        '''
        self.sendBeams.emit(self.beams)
        return self.beams

    def add_attribute(self,attribute):
        # to be used from measurement each attribute should consist of a tuple of name and content
        attribute_name, attribute_value = attribute
        with h5py.File(self.temp_filename, 'a') as hf:
            hf["spectra"].attrs[attribute_name] = attribute_value

    def change_send_idx(self, x_idx, y_idx):
        # this function changes the parameter that are sent to parameter display.
        self.send_x_idx = list(self.parameter_queue)[x_idx]
        self.send_y_idx = list(self.parameter_queue)[y_idx]

    def overwrite_popup(self):
        # not used currently, as time stamp prevents to have overwrite scenarios.
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
        # not used currently, to be implemented to continue aborted measurements/ after software crash
        pass

    def calibration_to_dict(calib_dict):
        """
            Convert calibration dict to HDF5-safe dict.
            - Polynomials are converted to {'_type': 'Polynomial', 'coef': [...]}
            - Other dicts, arrays, lists, and scalars are preserved.
        """
        safe_dict = {}
        for k, v in calib_dict.items():
            if isinstance(v, np.ndarray):
                safe_dict[k] = v
            elif isinstance(v, (int, float, str, bool)):
                safe_dict[k] = v
            elif isinstance(v, dict):
                safe_dict[k] = DataHandling.calibration_to_dict(v)  # recurse
            elif isinstance(v, P):  # Polynomial
                safe_dict[k] = {
                    "_type": "Polynomial",
                    "coef": v.coef,  # numpy array, no .tolist()
                    "domain": v.domain,  # numpy array, no .tolist()
                    "window": v.window  # numpy array, no .tolist()
                }
            else:
                safe_dict[k] = str(v)
        return safe_dict

    def dict_to_calibration(saved_dict):
        """
            Convert HDF5-loaded calibration dict back to proper types.
            - Polynomials are reconstructed with coef, domain, window
            - Arrays, scalars, and nested dicts are preserved
        """
        restored = {}
        for k, v in saved_dict.items():
            if isinstance(v, dict) and v.get("_type") == "Polynomial":
                restored[k] = P(
                    coef=v["coef"],
                    domain=v["domain"],
                    window=v["window"]
                )
            elif isinstance(v, dict):
                restored[k] = DataHandling.dict_to_calibration(v)
            else:
                restored[k] = v
        return restored
        
    def update_spec_length(self, new_length):
        """
        Update the spectrometer buffer length and reset data buffers.

        Parameters:
            new_length (int): The new number of pixels in the spectrum.
        """
        if isinstance(new_length, tuple):
            self.speclength = new_length[1]  # or [0], whichever is intended
        else:
            self.speclength = new_length

        # Reset spectrum buffer
        self.spec = np.zeros((self.speclength, 0))  # zero columns, rows = new_length

        # Reset wavelength buffer if you store wavelengths
        if hasattr(self, 'wls'):
            self.wls = np.zeros(self.speclength)

        # preallocate data arrays depending on data dimension (1D or 2D).
        if self.data_dim == 1:
            self.spec = np.empty([self.speclength, 0])
            self.background = np.zeros([self.speclength, 1])
            self.wls = np.empty([self.speclength, 1])
        else:
            self.spec = np.empty([0, self.speclength[0], self.speclength[1]])
            self.background = np.zeros([1, self.speclength[0], self.speclength[1]])
            self.wls = np.empty([self.speclength[1], 1])

        """ A background belongs to the spectrometer it was taken on, so changing spectrometer drops
        it. It used to be reallocated with np.empty while the correction checkbox stayed ticked,
        which silently turned a valid background into uninitialised memory. """
        if self.has_background:
            logger.warning('%s Background dropped: the spectrum length changed to %s'
                           % (datetime.datetime.now(), self.speclength))
        self.has_background = False
        self.background_warned = False

        # Optional: log the update
        logger.info(f"Updated spec_length to {self.speclength} and reset buffers.")

    def close(self):
        """Safely stop Qt thread + worker before re-instantiating DataHandling."""

        # 1. Stop worker thread safely (if it has a stop flag)
        try:
            if hasattr(self, "BufferWorker") and self.BufferWorker is not None:
                self.BufferWorker.terminate = True  # your custom flag (optional)
        except:
            pass

        # 2. Disconnect signals (VERY important)
        try:
            if hasattr(self, "bufferSaveSignal"):
                self.bufferSaveSignal.disconnect()
        except:
            pass

        # 3. Quit Qt thread event loop
        try:
            if hasattr(self, "thread") and self.thread is not None:
                self.thread.quit()
                self.thread.wait()   # blocks until fully stopped
        except:
            pass

        # 4. Delete worker safely
        try:
            if hasattr(self, "BufferWorker") and self.BufferWorker is not None:
                self.BufferWorker.deleteLater()
                self.BufferWorker = None
        except:
            pass

        # 5. Delete thread safely
        try:
            if hasattr(self, "thread") and self.thread is not None:
                self.thread.deleteLater()
                self.thread = None
        except:
            pass


class BufferWorker(QtCore.QObject):
    """ Buffer worker saves data to a temp file.
    It is started every time a given amount of data has been acquired and receives signals with the corresponding data"""

    def __init__(self, temp_filename, data_dim, done_event=None):
        super(BufferWorker, self).__init__()
        self.temp_filename = temp_filename
        self.data_dim = data_dim
        self.done_event = done_event
        self.firstbuffer = True
        self.terminate = False
        # check if folder for buffer exists
        temp_folder = os.path.dirname(temp_filename)
        if not os.path.isdir(temp_folder):
            print(f'No {temp_folder} folder, create folder')
            os.makedirs(temp_folder)
        else:
            pass

    @QtCore.pyqtSlot(object, object, object, object)
    def save_buffer(self,spec,wls,parameter_queue,parameter_measured):
        # check for first buffer saving to initialize data array
        t1 = time.time()
        if self.firstbuffer:
            try:
                os.remove(self.temp_filename) # clear temp file
            except FileNotFoundError:
                pass # no file to delete
            with h5py.File(self.temp_filename, 'w') as hf:
                if self.data_dim == 1:
                    hf.create_dataset("spectra", data=spec, compression="gzip", chunks=True,
                                      maxshape=(np.shape(spec)[0], None))
                else:
                    # float16 is used for camera pixels, as max values is 65504.
                    hf.create_dataset("spectra", data=spec, compression="gzip", chunks=True, maxshape=(None,np.shape(spec)[1],np.shape(spec)[2]),dtype='float16')
                hf["spectra"].attrs["xaxis"] = wls
                hf.create_dataset("parameter", data=parameter_measured, compression="gzip", chunks=True, maxshape=(np.shape(parameter_measured)[0],None))
                hf["parameter"].attrs["parameter_keys"] = list(parameter_queue.keys())
            logger.info('%s First buffer saved' %datetime.datetime.now())
            self.firstbuffer = False
        else:
            try:
                with h5py.File(self.temp_filename, 'a') as hf:
                    if self.data_dim == 1:
                        hf["spectra"].resize((hf["spectra"].shape[1] + spec.shape[1]), axis=1)
                        hf["spectra"][:, -spec.shape[1]:] = spec
                    else:
                        hf["spectra"].resize((hf["spectra"].shape[0] + spec.shape[0]), axis=0)
                        hf["spectra"][-spec.shape[0]:] = spec
                    hf["parameter"].resize((hf["parameter"].shape[1] + parameter_measured.shape[1]), axis=1)
                    hf["parameter"][:, -parameter_measured.shape[1]:] = parameter_measured
            except TypeError:
                logger.warning('% s Saving failed. Did you already save?' %datetime.datetime.now())
        """ Release save_data(). Left unset if the write above raised, so save_data() times out and
        refuses to copy rather than copying a half-written file. """
        if self.done_event is not None:
            self.done_event.set()
