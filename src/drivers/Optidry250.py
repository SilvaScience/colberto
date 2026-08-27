from PyQt5 import QtCore
import time
from collections import defaultdict
import pyvisa
import numpy as np

class CryoPasqal(QtCore.QThread):
    """
    Main driver class for the Optidry 250 Cryostat.
    Inherits from QThread to integrate smoothly with PyQt5 applications.
    Manages state dictionaries, hardware commands, and the background polling worker.
    """
    # MANDATORY class variables for the GUI tree structure
    name = 'CryoPasqal'
    type = 'Cryostat'

    def __init__(self, port_com):
        super(CryoPasqal, self).__init__()
        
        # 1. Initialize nested dictionary for detailed parameter info (value, limits, read-only flags)
        self.parameter_display_dict = defaultdict(dict)
        
        # --- Setpoint and Loop settings ---
        self.parameter_display_dict['Set_T']['val'] = 300.0
        self.parameter_display_dict['Set_T']['unit'] = ' K'
        self.parameter_display_dict['Set_T']['min'] = 0
        self.parameter_display_dict['Set_T']['max'] = 400
        self.parameter_display_dict['Set_T']['read'] = False # False means it is writable by the user

        self.parameter_display_dict['Regulation_Loop']['val'] = 1
        self.parameter_display_dict['Regulation_Loop']['unit'] = ' loop'
        self.parameter_display_dict['Regulation_Loop']['min'] = 1
        self.parameter_display_dict['Regulation_Loop']['max'] = 2
        self.parameter_display_dict['Regulation_Loop']['read'] = False
        
        # --- Temperatures (Channels A to E) ---
        # Note: 'read': True means these are sensor values, not meant to be manually overwritten
        self.parameter_display_dict['ChannelA_T']['val'] = 300.0
        self.parameter_display_dict['ChannelA_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelA_T']['min'] = 0
        self.parameter_display_dict['ChannelA_T']['max'] = 400
        self.parameter_display_dict['ChannelA_T']['read'] = True

        self.parameter_display_dict['ChannelB_T']['val'] = 300.0
        self.parameter_display_dict['ChannelB_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelB_T']['min'] = 0
        self.parameter_display_dict['ChannelB_T']['max'] = 400
        self.parameter_display_dict['ChannelB_T']['read'] = True

        self.parameter_display_dict['ChannelC_T']['val'] = 300.0
        self.parameter_display_dict['ChannelC_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelC_T']['min'] = 0
        self.parameter_display_dict['ChannelC_T']['max'] = 400
        self.parameter_display_dict['ChannelC_T']['read'] = True

        self.parameter_display_dict['ChannelD_T']['val'] = 300.0
        self.parameter_display_dict['ChannelD_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelD_T']['min'] = 0
        self.parameter_display_dict['ChannelD_T']['max'] = 400
        self.parameter_display_dict['ChannelD_T']['read'] = True

        self.parameter_display_dict['ChannelE_T']['val'] = 300.0
        self.parameter_display_dict['ChannelE_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelE_T']['min'] = 0
        self.parameter_display_dict['ChannelE_T']['max'] = 400
        self.parameter_display_dict['ChannelE_T']['read'] = True
        
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

        # 2. Create flat parameter_dict mapping values (used for quick access by the GUI)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # --- History for stability calculation ---
        self.temp_history = []
        self.stability_threshold = 0.05 # Delta T (Kelvin) allowed to be considered stable
        self.stability_window = 30      # Number of recent samples required to check stability

        # --- PyVISA management and communication lock ---
        self.port_com = port_com
        self.rm = pyvisa.ResourceManager()
        self.is_connected = False
        
        # Mutex ensures the background thread and main thread don't send/receive VISA commands simultaneously
        self.visa_mutex = QtCore.QMutex() 
        self.Opti = None

        # Attempt to open hardware connection
        try:
            self.Opti = self.rm.open_resource(
                self.port_com,
                baud_rate=115200,
                data_bits=8,
                parity=pyvisa.constants.Parity.none,
                stop_bits=pyvisa.constants.StopBits.one,
                write_termination='\n',
                read_termination='\n',
                timeout=2000
            )
            self.is_connected = True
        except Exception as e:
            print(f"VISA initialization error for the Optidry250: {e}")
            self.is_connected = False

        # Initialize and start the background polling worker
        self.UpdateWorker = PascalWorker(self.Opti, self.visa_mutex, self.is_connected)
        
        # Connect the worker's data emission signal to the update_all_data slot
        self.UpdateWorker.new_T.connect(self.update_all_data)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        """
        Dispatcher method called by main.py/GUI to update a parameter.
        Updates internal dictionaries and fires specific hardware commands.
        """
        if not self.is_connected: return

        # Update local states
        self.parameter_dict[parameter] = value
        if parameter in self.parameter_display_dict:
            self.parameter_display_dict[parameter]['val'] = value

        # Route to appropriate hardware command
        if parameter == 'Set_T':
            loop = int(self.parameter_dict.get('Regulation_Loop', 1))
            self.set_temperature_setpoint(loop, float(value))
        elif parameter in ['Pid_P', 'Pid_I', 'Pid_D']:
            loop = int(self.parameter_dict.get('Regulation_Loop', 1))
            p = float(self.parameter_dict.get('Pid_P', 0.0))
            i = float(self.parameter_dict.get('Pid_I', 0.0))
            d = float(self.parameter_dict.get('Pid_D', 0.0))
            self.set_pid_parameters(loop, p, i, d)
        elif parameter == 'OnOff_comp':
            self.set_compressor_state(bool(int(value)))

    def update_all_data(self, data_list):
        """
        Slot function that receives new sensor data from the background worker.
        Updates internal dictionary states and triggers stability calculations.
        """
        # Ensure data integrity before unpacking
        if not isinstance(data_list, list) or len(data_list) < 8:
            return
            
        # Helper function to safely update both dictionaries
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
        assign_val('OnOff_comp', int(data_list[7]))

        # Calculate stability based on the primary temperature channel (ChannelA_T)
        self.calculate_stability(data_list[0])

    def calculate_stability(self, current_temp):
        """
        Maintains a rolling window of temperature readings to determine system stability.
        Updates the 'Stability' parameter to "Stable" or "In progress".
        """
        self.temp_history.append(current_temp)
        
        # Keep window size clamped
        if len(self.temp_history) > self.stability_window:
            self.temp_history.pop(0)

        status = "In progress"
        
        # Only evaluate if we have a full window of data
        if len(self.temp_history) >= self.stability_window:
            temp_range = max(self.temp_history) - min(self.temp_history)
            if temp_range <= self.stability_threshold:
                status = "Stable"

        self.parameter_dict['Stability'] = status
        self.parameter_display_dict['Stability']['val'] = status

    # --- Hardware Command Methods ---
    
    def set_temperature_setpoint(self, loop, target_temp):
        if not self.is_connected: return
        try:
            # Lock the mutex to prevent the polling worker from interfering
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"SOURce:TEMPerature:SPOint {loop}, {target_temp}")
            print(f"Loop {loop} setpoint updated to: {target_temp} K")
        except Exception as e:
            print(f"Error while sending the setpoint: {e}")

    def set_heater_range(self, loop, range_level):
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"SOURCE:HEATer:RANGe {loop}, {range_level}")
            print(f"Loop {loop} Heater Range updated to: {range_level}")
        except Exception as e:
            print(f"Error while sending the Heater Range: {e}")

    def set_pid_parameters(self, loop, p, i, d):
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            # Send P, I, and D values via SCPI commands
            self.Opti.write(f"SOURce:TEMPerature:PROPortional {loop}, {p}")
            self.Opti.write(f"SOURce:TEMPerature:INTegral {loop}, {i}")
            self.Opti.write(f"SOURce:TEMPerature:DERivative {loop}, {d}")
            print(f"Loop {loop} PID parameters updated: P={p}, I={i}, D={d}")
        except Exception as e:
            print(f"Error while sending the PID parameters: {e}")

    def set_compressor_state(self, state_on):
        if not self.is_connected: return
        etat_str = "ON" if state_on else "OFF"
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"CONTrol:COMPressor:STATe {etat_str}")
            print(f"Compressor set to: {etat_str}")
        except Exception as e:
            print(f"Compressor command error: {e}")

    def reset_compressor_alarm(self):
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write("CONTrol:COMPressor:RESet")
            print("Alarm reset command sent.")
        except Exception as e:
            print(f"Error during alarm reset: {e}")


class PascalWorker(QtCore.QThread):
    """
    Background worker thread that continually polls the Cryostat hardware.
    Using a separate thread prevents the GUI from freezing during I/O delays.
    """
    # Signal emitted containing the [temps, pressures, comp_state] list
    new_T = QtCore.pyqtSignal(list)

    def __init__(self, instrument_visa, visa_mutex, is_connected):
        super(PascalWorker, self).__init__()
        self.stop = False
        self.waitTime = 1.0  # Poll interval in seconds
        self.instrument_visa = instrument_visa 
        self.visa_mutex = visa_mutex
        self.is_connected = is_connected

    def run(self):
        """
        The main loop executed by the thread.
        """
        while not self.stop:
            if self.is_connected and self.instrument_visa is not None:
                data = self.read_all_hardware_data()
                if data:
                    self.new_T.emit(data) # Broadcast the data to the main thread
            time.sleep(self.waitTime)

    def read_all_hardware_data(self):
        """
        Fetches live data from the hardware using SCPI query commands.
        Returns a formatted list of [T1, T2, T3, T4, T5, P1, P2, Comp_State].
        """
        try:
            # Lock the mutex so we don't query while the main thread is sending a setting
            locker = QtCore.QMutexLocker(self.visa_mutex)    
            
            # Query channels 1 through 5 for temperature
            rep_temp = self.instrument_visa.query("MEASure:TEMPerature? (@1,2,3,4,5)")
            temps_float = [float(t) for t in rep_temp.strip().split(',')]
            
            # Query channels 1 and 2 for pressure
            rep_press = self.instrument_visa.query("MEASure:PRESSure? (@1,2)")
            press_float = [float(p) for p in rep_press.strip().split(',')]
            
            # Query compressor status
            rep_comp = self.instrument_visa.query("CONTrol:COMPressor:STATe?")
            comp_state = 1 if "ON" in rep_comp.upper() else 0
            
            # Unlock immediately after queries are complete
            locker.unlock()
            
            return temps_float + press_float + [comp_state]
            
        except Exception as e:
            # Fallback values if the read times out or fails (prevents crashing)
            return [300.0, 300.0, 300.0, 300.0, 300.0, 101300.0, 101300.0, 0]
