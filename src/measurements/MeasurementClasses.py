"""
Measurement classes for different types of measurements. Each measurement creates a new thread that runs until the
measurement has finished or was requested to stop. Measurements can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each measurements, parameter are read from Main script and remain
until the measurement has finished.
"""

import time
from PyQt5 import QtCore
import numpy as np
import re


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
        if not self.terminate:  # check whether stopping measurement is called
            self.sendProgress.emit(50)
            self.wls = np.array(self.spectrometer.getWavelength())
            self.take_spectrum()
            print(time.strftime('%H:%M:%S') + ' Finished')
            self.sendProgress.emit(100)

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.getIntensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


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
        while not self.terminate:  # check whether stopping measurement is called
            t = time.time()
            self.sendProgress.emit(50)
            self.wls = np.array(self.spectrometer.getWavelength())
            self.spec = np.array(self.spectrometer.getIntensities())
            self.sendClear.emit()
            self.sendSpectrum.emit(self.wls, self.spec)

            # limit too fast acquistion for computation
            if time.time() - t < 0.02:
                time.sleep(0.02)

        # Finish measurement when loop is terminated
        print(time.strftime('%H:%M:%S') + ' Finished')
        self.sendProgress.emit(100)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


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
        print('emit start time ')

    def run(self):
        while not self.terminate:  # loop runs until requested stop
            t1 = time.time()
            self.wls = np.array(self.spectrometer.getWavelength())
            self.spec = np.array(self.spectrometer.getIntensities())

            # send data
            self.sendSpectrum.emit(self.wls, self.spec)
            progress = 50
            self.sendProgress.emit(progress)

            # limit too fast acquistion for computation
            if time.time() - t1 < 0.02:
                time.sleep(0.02)
        print(time.strftime('%H:%M:%S') + ' Finished')
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
        print(filename[:filename.rfind('/') + 1] + 'Background')
        self.comments = comments
        self.terminate = False

    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
            self.summedspec = np.array(self.spectrometer.getIntensities())
            for i in range(self.scans - 1):
                self.sendProgress.emit((i + 1) / self.scans * 100)
                self.wls = np.array(self.spectrometer.getWavelength())
                self.spec = np.array(self.spectrometer.getIntensities())
                self.summedspec = self.summedspec + self.spec
            self.spec = self.summedspec / self.scans
            self.sendSpectrum.emit(self.wls, self.spec)
            self.sendSave.emit(self.filename, self.comments)
            self.sendProgress.emit(100)
            print(time.strftime('%H:%M:%S') + 'Background acquired')

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class TSeriesMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendTemperature = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, T_series, T_stab_time, two_sources, ref_power, int_time_WL, int_time_orpheus,
                 spectra_avg, power_dep, filter_pos, int_times):
        super(TSeriesMeasurement, self).__init__()
        self.Spectrometer = devices['spectrometer']
        self.cryostat = devices['cryostat']
        self.T_series = T_series
        self.T_stab_time = T_stab_time
        self.two_sources = two_sources
        self.ref_power = ref_power
        self.int_time_WL = int_time_WL
        self.int_time_orpheus = int_time_orpheus
        self.spectra_avg = spectra_avg
        self.wls = []
        self.spec = []
        self.terminate = False
        self.power_dep = power_dep
        self.filter_ard_pos = []
        self.filter_thor_pos = []
        self.int_times = []
        try:
            for s in re.split(',', filter_pos):
                self.filter_ard_pos = np.append(self.filter_ard_pos, int(s[1:]))
                self.filter_thor_pos = np.append(self.filter_thor_pos, int(s[0]))
            for s in re.split(',', int_times):
                self.int_times = np.append(self.int_times, int(s))
        except ValueError:
            print('WARNING: Assigning filter pos did not work')

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run T Series Measurement')
        if not self.terminate:
            self.sendProgress.emit(1)
            self.wls = np.array(self.Spectrometer.getWavelength())
            n = 0
            for temperature in self.T_series:
                n = n + 1
                self.sendParameter.emit('set_T', temperature)

                # wait for temperature
                T_current = self.cryostat.parameter_dict['current_T']
                while not abs(T_current - temperature) < 0.5:
                    if not self.terminate:
                        T_current = self.cryostat.parameter_dict['current_T']
                        print(time.strftime('%H:%M:%S') + ' Waiting for Temperature')
                        time.sleep(5)
                print(time.strftime('%H:%M:%S') + ' Temperature setpoint reached: ' + str(temperature) + ' K')
                print(time.strftime('%H:%M:%S') + ' Let stabilize')
                time.sleep(self.T_stab_time)

                # measure
                if not self.terminate:
                    if not self.two_sources:
                        for m in range(self.spectra_avg):
                            self.spec = np.array(self.Spectrometer.getIntensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' Spectrum acquired')

                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)

                    else:
                        if not self.power_dep:
                            self.sendParameter.emit('int_time', self.int_time_orpheus)
                            self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                            time.sleep(2)
                            for m in range(self.spectra_avg):
                                self.spec = np.array(self.Spectrometer.getIntensities())
                                self.sendSpectrum.emit(self.wls, self.spec)
                                print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')

                            self.sendParameter.emit('int_time', self.int_time_WL)
                            self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
                            time.sleep(2)
                        else:
                            for k in range(len(self.int_times)):
                                if not self.terminate:
                                    self.sendParameter.emit('int_time', self.int_times[k])
                                    # set intensity filter
                                    self.sendParameter.emit('filter_wheel', self.filter_ard_pos[k])
                                    self.sendParameter.emit('filter_pos', self.filter_thor_pos[k])
                                    # trigger spectrometer to settle to new int time
                                    if not self.int_time_orpheus == self.int_times[k]:
                                        print(time.strftime('%H:%M:%S') + ' Int time changed, trigger spectrometer and '
                                                                          'wait to stabilize changes')
                                        self.Spectrometer.getIntensities()
                                        time.sleep(2)
                                    self.int_time_orpheus = self.int_times[k]
                                    waittime = 1 + self.int_times[k] / 1000
                                    if waittime < 2:
                                        waittime = 2
                                    time.sleep(waittime)
                                    self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                                    time.sleep(2)
                                    for m in range(self.spectra_avg):
                                        self.spec = np.array(self.Spectrometer.getIntensities())
                                        self.sendSpectrum.emit(self.wls, self.spec)
                                        print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')
                                    self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
                                    time.sleep(2)
                            self.sendParameter.emit('int_time', self.int_time_WL)

                        self.sendParameter.emit('shutter2', 100)  # open WL shutter
                        time.sleep(2)
                        self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter again
                        time.sleep(2)

                        for m in range(self.spectra_avg):
                            self.spec = np.array(self.Spectrometer.getIntensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' WL Spectrum acquired')

                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)
                        self.sendParameter.emit('shutter2', 0)  # close WL shutter
                        time.sleep(2)
                        if self.terminate:
                            self.sendProgress.emit(100)

        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class TwoPhotonMeasurement(QtCore.QThread):
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, devices, parameter, wave_array, ref_wave, ref_power, spectra_number, scan_number, skip_power,power_correction):
        super(TwoPhotonMeasurement, self).__init__()

        self.Spectrometer = devices['spectrometer']
        self.orpheus = devices['orpheus']
        self.powermeter = devices['powermeter']
        self.arduino = devices['arduino_shutters']
        self.thorlabs_fw = devices['thorlabs_fw']
        self.ref_wave = ref_wave
        self.ref_power = ref_power
        self.wave_array = wave_array
        self.spectra_number = spectra_number
        self.scan_number = scan_number
        self.skip_power = skip_power
        self.wls = []
        self.spec = []
        self.terminate = False
        self.skip_long_term_power = False
        self.coarse_check = False
        try:
            print(power_correction)
            print(type(power_correction))
            self.power_array = ((ref_wave / wave_array) * ref_power) / power_correction * np.min(power_correction)
        except:
            print('WARNING: power correction not applied')
            self.power_array = ((ref_wave / wave_array) * ref_power)

        # print(self.power_array)

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run Two Photon Measurement')
        self.sendParameter.emit('filter_pos', 12)
        progress = 0
        n = 0
        for i in range(self.scan_number):
            if not self.terminate:
                self.sendProgress.emit(1)
                self.wls = np.array(self.Spectrometer.getWavelength())

                for idx, wavelength in enumerate(self.wave_array):
                    self.coarse_check = False
                    self.sendParameter.emit('set_wl', wavelength)
                    self.sendParameter.emit('wl', wavelength)
                    print(f'Wait to set powermeter to {wavelength: .1f} nm')
                    time.sleep(10)  # wait for powermeter to change

                    # wait for wavelength
                    wl_current = self.orpheus.parameter_dict['current_wl']
                    while not wl_current == wavelength and not self.terminate:
                        print(f'Wait for WL {wavelength: .1f} nm to set')
                        time.sleep(2)
                        wl_current = self.orpheus.parameter_dict['current_wl']

                    print(f'Set power to {self.power_array[idx]: .1f} nW at ref')

                    if not self.skip_power:
                        # calculate expected filter pos:
                        coarse_power = False
                        while not coarse_power and not self.terminate:
                            # arduino decays 1 order of magnitude in 127deg
                            curr_power = self.powermeter.parameter_dict['current_power']
                            pos_curr = self.arduino.parameter_dict['filter_wheel']
                            pos_change = 127 * np.log10(self.power_array[idx] / curr_power)
                            pos_exp = round(pos_curr + pos_change)
                            if pos_exp < 1:
                                new_thor_pos = self.thorlabs_fw.parameter_dict['filter_pos'] + 1
                                if new_thor_pos > 12:
                                    print('Thorlabs filterwheel max reached. Skip.')
                                    coarse_power = True
                                else:
                                    self.sendParameter.emit('filter_pos', new_thor_pos)
                                time.sleep(2)
                            elif pos_exp > 250:
                                new_thor_pos = self.thorlabs_fw.parameter_dict['filter_pos'] - 1
                                if new_thor_pos - 1 < 1:
                                    print('Thorlabs filterwheel min reached. Skip.')
                                    coarse_power = True
                                else:
                                    self.sendParameter.emit('filter_pos', new_thor_pos)
                                time.sleep(2)

                            else:
                                self.sendParameter.emit('filter_wheel', pos_exp)
                                time.sleep(1)
                                coarse_power = True
                        print(f'Filter set to {pos_exp} deg, check fine power')


                        # fine adjust power
                        fine_power = False

                        while not fine_power and not self.terminate:
                            curr_power = self.powermeter.parameter_dict['current_power']
                            delta_power = self.power_array[idx] / curr_power
                            pos_exp = self.arduino.parameter_dict['filter_wheel']
                            if delta_power > 1.03:
                                pos_exp = pos_exp + 2
                                if pos_exp > 300:
                                    if self.thorlabs_fw.parameter_dict['filter_pos'] > 1:
                                        self.sendParameter.emit('filter_pos', self.thorlabs_fw.parameter_dict['filter_pos'] + 1)
                                    else:
                                        print('Max global power reached. Skip')
                                        fine_power = True
                                else:
                                    self.sendParameter.emit('filter_wheel', pos_exp)
                                time.sleep(2)
                            elif delta_power < 0.97:
                                pos_exp = pos_exp - 2
                                self.sendParameter.emit('filter_wheel', pos_exp)
                                time.sleep(2)
                            else:
                                fine_power = True
                        print(f'Filter set to {pos_exp} deg, check long term power')

                        # long term power check.
                        while not self.coarse_check and not self.terminate:
                            time.sleep(6)
                            avg_power_pos0 = self.powermeter.parameter_dict['avg_power']
                            self.sendParameter.emit('filter_wheel', pos_exp + 2)
                            time.sleep(1)
                            self.sendParameter.emit('filter_wheel', pos_exp + 2)
                            time.sleep(5)
                            avg_power_pos1 = self.powermeter.parameter_dict['avg_power']
                            self.sendParameter.emit('filter_wheel', pos_exp - 2)
                            time.sleep(1)
                            self.sendParameter.emit('filter_wheel', pos_exp - 2)
                            time.sleep(5)
                            avg_power_pos2 = self.powermeter.parameter_dict['avg_power']
                            delta0 = abs(avg_power_pos0 - self.power_array[idx])
                            delta1 = abs(avg_power_pos1 - self.power_array[idx])
                            delta2 = abs(avg_power_pos2 - self.power_array[idx])
                            if delta1 < delta0:
                                pos_exp = pos_exp + 2
                                if pos_exp > 300:
                                    self.coarse_check = True
                                    print('Max global power reached, power mismatch is:' +
                                          f'{delta0 / self.power_array[idx] * 100 : .1f} percent' +
                                          f'\n Averaged power: {avg_power_pos0 : .1f} Set power: {self.power_array[idx] :.1f}')
                                else:
                                    print('Not in optimal power settings, increase set angle')
                                self.sendParameter.emit('filter_wheel', pos_exp)
                            elif delta2 < delta0:
                                pos_exp = pos_exp - 2
                                print('Not in optimal power settings, decrease set angle')
                                self.sendParameter.emit('filter_wheel', pos_exp)
                            else:
                                self.coarse_check = True
                                print('Optimum power reached, power mismatch is:' +
                                      f'{delta0 / self.power_array[idx] * 100 : .1f} percent' +
                                      f'\n Averaged power: {avg_power_pos0 : .1f} Set power: {self.power_array[idx] :.1f}')
                                self.sendParameter.emit('filter_wheel', pos_exp)
                        print(time.strftime('%H:%M:%S') + ' Power set')
                    else:
                        print('Long term power skipped')
                        self.skip_long_term_power = False
                    power = self.powermeter.parameter_dict['avg_power']
                    n = n + 1
                    progress = progress + 1

                    # acquire
                    print(time.strftime('%H:%M:%S') + f' Power Output Reached: {power: .1f} nW')
                    time.sleep(2)
                    self.sendParameter.emit('shutter1', 100)
                    time.sleep(2 + self.powermeter.parameter_dict['avg_time'])
                    if not self.terminate:
                        for m in range(self.spectra_number):
                            self.spec = np.array(self.Spectrometer.getIntensities())
                            progress = (n + i) / len(self.power_array) / self.scan_number * 100
                            self.sendSpectrum.emit(self.wls, self.spec)
                            self.sendProgress.emit(progress)
                            print(time.strftime('%H:%M:%S') + ' Spectrum acquired')
                    else:
                        break
                    self.sendParameter.emit('shutter1', 0)

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


# Measurement to acquire spectra according to a time array defined by the user. Shutter commands are enabled
class KineticMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, devices, parameter, kinetic_interval):
        super(KineticMeasurement, self).__init__()
        self.Spectrometer = devices['spectrometer']
        #self.orpheus = devices['thorlabs_shutter']
        self.kinetic_interval = kinetic_interval
        self.wls = []
        self.spec = []
        self.terminate = False
        self.t_curr_step = 0
        self.t0 = 0
        try:  # extract max time of measurement series to calculate progress
            self.max_time = float(re.findall('[0-9]+[.]', kinetic_interval[-1])[0])
        except:
            try:
                self.max_time = float(re.findall('[0-9]+[.]', kinetic_interval[-2])[0])
            except:
                self.max_time = float(kinetic_interval[-1][0])

    def run(self):
        print(time.strftime('%H:%M:%S') + 'Run Kinetic Measurement')
        if not self.terminate:
            # get wls and start time
            self.wls = np.array(self.Spectrometer.getWavelength())
            self.t0 = time.time()

            # get commands from kinetic_interval
            for k in self.kinetic_interval:
                if not self.terminate:
                    # shutter command or waiting time
                    if isinstance(k, str):  # shutter command
                        if k == 'open':
                            print('open shutter')
                            self.sendParameter.emit('fast_shutter', 100)
                            wait = 0.05
                            time.sleep(wait)
                        elif k == 'close':
                            print('close shutter')
                            self.sendParameter.emit('fast_shutter', 0)
                            wait = 0.05
                            time.sleep(wait)

                        # open, acquire, close and wait
                        elif k[0] == 'p':
                            # set spectrometer in probe trigger mode
                            self.Spectrometer.probe_trigger = True
                            self.t_curr_step = float(k[1:])
                            # wait
                            wait_time = self.t0 + float(k[1:]) - time.time()
                            if wait_time > 0:
                                time.sleep(wait_time)
                            else:
                                print('Waiting time before probe cycle negative:' + str(wait_time))
                            self.probe_cycle()
                            self.sendProgress.emit(float(k[1:]) / self.max_time * 100)

                    # acquire spectrum and wait
                    elif isinstance(k, np.ndarray):  # waiting command
                        for j in k:
                            if not self.terminate:
                                self.t_curr_step = j
                                self.spec = np.array(self.Spectrometer.getIntensities())
                                self.sendSpectrum.emit(self.wls, self.spec)
                                self.sendProgress.emit(j / self.max_time * 100)
                                t3 = time.time()
                                wait_time = self.t0 + self.t_curr_step - t3

                                if wait_time > 0:
                                    time.sleep(wait_time)
                                else:
                                    print('Waiting time negative:' + str(wait_time))

                    else:
                        print('Unknown instance in kinetic interval')

        self.sendProgress.emit(100)
        self.Spectrometer.probe_trigger = False
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    # helper functions  self.sendSpectrum.emit(self.wls, self.spec)
    def probe_cycle(self):
        # open shutter
        t1 = time.time()
        self.sendParameter.emit('fast_shutter', 100)
        # acquire
        if not self.terminate:
            self.spec = np.array(self.Spectrometer.getIntensities())
            # close shutter
            self.sendParameter.emit('fast_shutter', 0)
            self.sendSpectrum.emit(self.wls, self.spec)
            t2 = time.time()
            print('Open time: ' + str(t2 - t1))

            #  initiate controlled stop by enableing terminate statement, that is frequently queried in run code

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class SetPowerMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, set_power, coarse_check):
        super(SetPowerMeasurement, self).__init__()
        self.orpheus = devices['orpheus']
        self.powermeter = devices['powermeter']
        self.arduino_shutters = devices['arduino_shutters']
        self.thorlabs_fw = devices['thorlabs_fw']
        self.set_power = set_power
        self.terminate = False
        self.coarse_check = coarse_check

    def run(self):

        # calculate expected filter pos:
        coarse_power = False
        while not coarse_power and not self.terminate:
            # arduino decays 1 order of magnitude in 127deg
            curr_power = self.powermeter.parameter_dict['current_power']
            pos_curr = self.arduino_shutters.parameter_dict['filter_wheel']
            pos_change = 127 * np.log10(self.set_power/curr_power)
            pos_exp = round(pos_curr + pos_change)
            if pos_exp < 1:
                new_thor_pos = self.thorlabs_fw.parameter_dict['filter_pos'] + 1
                self.sendParameter.emit('filter_pos', new_thor_pos)
                time.sleep(2)
            elif pos_exp > 250:
                new_thor_pos = self.thorlabs_fw.parameter_dict['filter_pos'] - 1
                self.sendParameter.emit('filter_pos', new_thor_pos)
                time.sleep(2)
            else:
                self.sendParameter.emit('filter_wheel', pos_exp)
                time.sleep(1)
                coarse_power = True
        print(f'Filter set to {pos_exp} deg, check fine power')

        # fine adjust power
        fine_power = False
        while not fine_power and not self.terminate:
            curr_power = self.powermeter.parameter_dict['current_power']
            delta_power = self.set_power/curr_power
            if delta_power > 1.05:
                pos_exp = pos_exp + 2
                self.sendParameter.emit('filter_wheel', pos_exp)
                time.sleep(2)
            elif delta_power < 0.95:
                pos_exp = pos_exp - 2
                self.sendParameter.emit('filter_wheel', pos_exp)
                time.sleep(2)
            else:
                fine_power = True
        print(f'Filter set to {pos_exp} deg, check long term power')

        # long term power check.
        while not self.coarse_check and not self.terminate:
            time.sleep(6)
            avg_power_pos0 = self.powermeter.parameter_dict['avg_power']
            self.sendParameter.emit('filter_wheel', pos_exp + 2)
            time.sleep(1)
            self.sendParameter.emit('filter_wheel', pos_exp + 2)
            time.sleep(5)
            avg_power_pos1 = self.powermeter.parameter_dict['avg_power']
            self.sendParameter.emit('filter_wheel', pos_exp - 2)
            time.sleep(1)
            self.sendParameter.emit('filter_wheel', pos_exp - 2)
            time.sleep(5)
            avg_power_pos2 = self.powermeter.parameter_dict['avg_power']
            delta0 = abs(avg_power_pos0 - self.set_power)
            delta1 = abs(avg_power_pos1 - self.set_power)
            delta2 = abs(avg_power_pos2 - self.set_power)
            if delta1 < delta0:
                pos_exp = pos_exp + 2
                print('Not in optimal power settings, increase set angle')
                self.sendParameter.emit('filter_wheel', pos_exp)
            elif delta2 < delta0:
                pos_exp = pos_exp - 2
                print('Not in optimal power settings, decrease set angle')
                self.sendParameter.emit('filter_wheel', pos_exp)
            else:
                self.coarse_check = True
                print('Optimum power reached, power mismatch is:' +
                      f'{delta0 / self.set_power * 100 : .1f} percent' +
                      f'\n Averaged power: {avg_power_pos0 : .1f} Set power: {self.set_power :.1f}')
                self.sendParameter.emit('filter_wheel', pos_exp)
        print(time.strftime('%H:%M:%S') + ' Power set')
        self.sendProgress.emit(100)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class PPSeriesMeasurement(QtCore.QThread):

    sendProgress = QtCore.pyqtSignal(float)
    sendTemperature = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, filter_pos, wait_time, acq_time, filename):
        super(PPSeriesMeasurement, self).__init__()
        self.UF_client = devices['uf_client']
        self.wait_time = wait_time
        self.acq_time = acq_time
        self.filename = filename
        self.filter_ard_pos = []
        self.filter_thor_pos = []
        self.int_times = []
        self.terminate = False
        for s in re.split(',', filter_pos):
            self.filter_ard_pos = np.append(self.filter_ard_pos, int(s[1:]))
            self.filter_thor_pos = np.append(self.filter_thor_pos, int(s[0]))

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run PP Series Measurement')
        finishtime = time.time() + len(self.filter_ard_pos) * (self.wait_time + 10)
        print('Series expected to finish at ' + time.strftime('%H:%M:%S', time.localtime(finishtime)))
        if not self.terminate:
            self.sendProgress.emit(1)
                # measure
            for k in range(len(self.filter_ard_pos)):
                if not self.terminate:
                    # set intensity filter
                    self.sendParameter.emit('filter_wheel', self.filter_ard_pos[k])
                    self.sendParameter.emit('filter_pos', self.filter_thor_pos[k])
                    waittime = 4
                    time.sleep(waittime)
                    self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                    time.sleep(2)
                    print(time.strftime('%H:%M:%S') + ' Take measurement at filter pos: ' + str(self.filter_thor_pos[k])
                          + str(self.filter_ard_pos[k]))

                    maxint = 20  #
                    save_path = self.filename + '_filterpos_' + str(int(self.filter_thor_pos[k])) + \
                               str(int(self.filter_ard_pos[k])) + '_' + time.strftime('%H_%M_%S') + '.ufs'
                    save_path = save_path.replace('/', '\\')
                    print(save_path)
                    self.UF_client.run_measurement(save_path, self.acq_time/1000)
                    endtime = time.time() + self.wait_time
                    finished = False
                    while not finished:
                        time.sleep(5)
                        if time.time() > endtime or self.terminate:
                            finished = True
                    self.sendProgress.emit(int(k/len(self.filter_ard_pos)*100))
            self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
            self.sendProgress.emit(100)

        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
