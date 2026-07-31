# -*- coding: utf-8 -*-
"""
Created on Thu Sep  1 13:26:53 2022

@author: NanoUltrafast2
Simulated cryostat driver used when no CryoPasqal hardware is available.
Mirrors the parameter names (drivers.Optidry250.CryoPasqal.parameter_display_dict)
and the command methods used by GUI.cryostattab.CryostatTab, so the dedicated
cryostat page and the generic parameter tree behave the same way in demo mode
as they do with real hardware.
"""

import numpy as np
from PyQt5 import QtCore
import time
from collections import defaultdict


class CryoDemo(QtCore.QThread):

    name = 'CryoDemo'
    type = 'Cryostat'

    def __init__(self):
        super(CryoDemo, self).__init__()

        self.parameter_display_dict = defaultdict(dict)

        # --- Setpoint and Loop settings ---
        self.parameter_display_dict['Set_T']['val'] = 5.0
        self.parameter_display_dict['Set_T']['unit'] = ' K'
        self.parameter_display_dict['Set_T']['min'] = 0
        self.parameter_display_dict['Set_T']['max'] = 400
        self.parameter_display_dict['Set_T']['read'] = False

        self.parameter_display_dict['Regulation_Loop']['val'] = 1
        self.parameter_display_dict['Regulation_Loop']['unit'] = ' loop'
        self.parameter_display_dict['Regulation_Loop']['min'] = 1
        self.parameter_display_dict['Regulation_Loop']['max'] = 2
        self.parameter_display_dict['Regulation_Loop']['read'] = False

        # --- Temperatures (Channels A to E) ---
        for channel in ['ChannelA_T', 'ChannelB_T', 'ChannelC_T', 'ChannelD_T', 'ChannelE_T']:
            self.parameter_display_dict[channel]['val'] = 5.0
            self.parameter_display_dict[channel]['unit'] = ' K'
            self.parameter_display_dict[channel]['min'] = 0
            self.parameter_display_dict[channel]['max'] = 400
            self.parameter_display_dict[channel]['read'] = True

        # --- Pressures (Channels F and G) ---
        self.parameter_display_dict['PressureF']['val'] = 101300.0
        self.parameter_display_dict['PressureF']['unit'] = ' Pa'
        self.parameter_display_dict['PressureF']['min'] = 0
        self.parameter_display_dict['PressureF']['max'] = 200000
        self.parameter_display_dict['PressureF']['read'] = True

        self.parameter_display_dict['PressureG']['val'] = 101300.0
        self.parameter_display_dict['PressureG']['unit'] = ' Pa'
        self.parameter_display_dict['PressureG']['min'] = 0
        self.parameter_display_dict['PressureG']['max'] = 200000
        self.parameter_display_dict['PressureG']['read'] = True

        # --- PID Parameters ---
        self.parameter_display_dict['Pid_P']['val'] = 0.0
        self.parameter_display_dict['Pid_P']['unit'] = ' P'
        self.parameter_display_dict['Pid_P']['min'] = 0
        self.parameter_display_dict['Pid_P']['max'] = 1000
        self.parameter_display_dict['Pid_P']['read'] = False

        self.parameter_display_dict['Pid_I']['val'] = 0.0
        self.parameter_display_dict['Pid_I']['unit'] = ' I'
        self.parameter_display_dict['Pid_I']['min'] = 0
        self.parameter_display_dict['Pid_I']['max'] = 1000
        self.parameter_display_dict['Pid_I']['read'] = False

        self.parameter_display_dict['Pid_D']['val'] = 0.0
        self.parameter_display_dict['Pid_D']['unit'] = ' D'
        self.parameter_display_dict['Pid_D']['min'] = 0
        self.parameter_display_dict['Pid_D']['max'] = 1000
        self.parameter_display_dict['Pid_D']['read'] = False

        # --- Status and Compressor ---
        self.parameter_display_dict['OnOff_comp']['val'] = 0
        self.parameter_display_dict['OnOff_comp']['unit'] = ' state'
        self.parameter_display_dict['OnOff_comp']['min'] = 0
        self.parameter_display_dict['OnOff_comp']['max'] = 1
        self.parameter_display_dict['OnOff_comp']['read'] = False

        self.parameter_display_dict['Stability']['val'] = "In progress"
        self.parameter_display_dict['Stability']['unit'] = ''
        self.parameter_display_dict['Stability']['read'] = True

        self.parameter_display_dict['Critical_State']['val'] = "OK"
        self.parameter_display_dict['Critical_State']['unit'] = ''
        self.parameter_display_dict['Critical_State']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # --- History for stability calculation ---
        self.temp_history = []
        self.stability_threshold = 0.05
        self.stability_window = 30

        # start simulated background polling worker
        self.UpdateWorker = DemoWorker(self.parameter_dict['ChannelA_T'], self.parameter_dict['Set_T'])
        self.UpdateWorker.new_T.connect(self.update_all_data)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        """Called by the generic parameter tree (banderole) for writable params."""
        self.parameter_dict[parameter] = value
        if parameter in self.parameter_display_dict:
            self.parameter_display_dict[parameter]['val'] = value

        if parameter == 'Set_T':
            self.UpdateWorker.target = value
        elif parameter == 'OnOff_comp':
            self.set_compressor_state(bool(int(value)))

    # --- Simulated hardware commands, mirror CryoPasqal's API used by CryostatTab ---

    def set_temperature_setpoint(self, loop, target_temp):
        self.parameter_dict['Set_T'] = target_temp
        self.parameter_display_dict['Set_T']['val'] = target_temp
        self.UpdateWorker.target = target_temp
        print(f'[Demo] Loop {loop} setpoint updated to: {target_temp} K')

    def set_heater_range(self, loop, range_level):
        print(f'[Demo] Loop {loop} Heater Range updated to: {range_level}')

    def set_pid_parameters(self, loop, p, i, d):
        self.parameter_dict['Pid_P'] = p
        self.parameter_dict['Pid_I'] = i
        self.parameter_dict['Pid_D'] = d
        print(f'[Demo] Loop {loop} PID parameters updated: P={p}, I={i}, D={d}')

    def set_compressor_state(self, state_on):
        self.parameter_dict['OnOff_comp'] = int(bool(state_on))
        self.parameter_display_dict['OnOff_comp']['val'] = int(bool(state_on))
        self.UpdateWorker.compressor_on = bool(state_on)
        print(f"[Demo] Compressor set to: {'ON' if state_on else 'OFF'}")

    def reset_compressor_alarm(self):
        self.parameter_dict['Critical_State'] = 'OK'
        self.parameter_display_dict['Critical_State']['val'] = 'OK'
        print('[Demo] Alarm reset command sent.')

    def update_all_data(self, data_list):
        """Slot receiving simulated sensor data from the background worker."""
        def assign_val(key, val):
            self.parameter_dict[key] = val
            self.parameter_display_dict[key]['val'] = val

        assign_val('ChannelA_T', data_list[0])
        assign_val('ChannelB_T', data_list[1])
        assign_val('ChannelC_T', data_list[2])
        assign_val('ChannelD_T', data_list[3])
        assign_val('ChannelE_T', data_list[4])
        assign_val('PressureF', data_list[5])
        assign_val('PressureG', data_list[6])

        self.calculate_stability(data_list[0])

    def calculate_stability(self, current_temp):
        self.temp_history.append(current_temp)
        if len(self.temp_history) > self.stability_window:
            self.temp_history.pop(0)

        status = "In progress"
        if len(self.temp_history) >= self.stability_window:
            temp_range = max(self.temp_history) - min(self.temp_history)
            if temp_range <= self.stability_threshold:
                status = "Stable"

        self.parameter_dict['Stability'] = status
        self.parameter_display_dict['Stability']['val'] = status


class DemoWorker(QtCore.QThread):
    """Background worker that simulates the cryostat drifting toward its setpoint."""

    new_T = QtCore.pyqtSignal(list)

    def __init__(self, initial_temp, initial_target):
        super(DemoWorker, self).__init__()
        self.stop = False
        self.waitTime = 0.5
        self.target = initial_target
        self.current_T = initial_temp
        self.compressor_on = False
        self.cooling_rate = 0.5  # K per tick toward target when compressor is on

    def run(self):
        while not self.stop:
            self.new_T.emit(self.simulate_step())
            time.sleep(self.waitTime)

    def simulate_step(self):
        # Drift current_T toward target, faster when the compressor is on
        rate = self.cooling_rate if self.compressor_on else self.cooling_rate * 0.1
        delta = self.target - self.current_T
        step = np.clip(delta, -rate, rate)
        noise = (np.random.rand() - 0.5) * 0.05
        self.current_T = self.current_T + step + noise

        pressure_f = 101300.0 + (np.random.rand() - 0.5) * 50
        pressure_g = 101300.0 + (np.random.rand() - 0.5) * 50

        # Other channels loosely track the primary channel with small fixed offsets
        return [
            self.current_T,
            self.current_T + 0.5,
            self.current_T + 1.0,
            self.current_T - 0.5,
            self.current_T - 1.0,
            pressure_f,
            pressure_g,
        ]
