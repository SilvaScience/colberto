from PyQt5 import QtCore
import time
from collections import defaultdict
import pyvisa
import numpy as np

class CryoPasqal(QtCore.QThread):
    # MANDATORY class variables for the GUI tree structure
    name = 'CryoPasqal'
    type = 'Cryostat'

    def __init__(self, port_com='ASRL9::INSTR'):
        super(CryoPasqal, self).__init__()
        
        # Initialization of the parameter dictionary for the main GUI
        self.parameter_dict = defaultdict()
        self.parameter_dict['Set_T'] = 300.0
        self.parameter_dict['OnOff_comp'] = 0
        self.parameter_dict['Regulation_Loop'] = 1  # 1 ou 2 selon la ComboBox
        
        # Temperatures (Channels A to E)
        self.parameter_dict['ChannelA_T'] = 300.0
        self.parameter_dict['ChannelB_T'] = 300.0
        self.parameter_dict['ChannelC_T'] = 300.0
        self.parameter_dict['ChannelD_T'] = 300.0
        self.parameter_dict['ChannelE_T'] = 300.0
        
       # Pressures (Channels F and G)
        self.parameter_dict['PressureF'] = 101300.0
        self.parameter_dict['PressureG'] = 101300.0
        
       # Statuses and PID
        self.parameter_dict['Pid_P'] = 0.0
        self.parameter_dict['Pid_I'] = 0.0
        self.parameter_dict['Pid_D'] = 0.0
        self.parameter_dict['Stability'] = "In progress"
        self.parameter_dict['Critical_State'] = "OK"

        # History for stability calculation (e.g., last 30 readings)
        self.temp_history = []
        self.stability_threshold = 0.05  # Stability threshold in Kelvin (e.g., +/- 50 mK)
        self.stability_window = 30       # Time window (in seconds if waitTime=1.0s)

       # PyVISA management and communication lock
        self.port_com = port_com
        self.rm = pyvisa.ResourceManager()
        self.is_connected = False
        self.visa_mutex = QtCore.QMutex()  # Native Qt Mutex to protect the serial port
        
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

        # Démarrage du Worker de lecture en arrière-plan
        self.UpdateWorker = PascalWorker(self.Opti, self.visa_mutex, self.is_connected)
        self.UpdateWorker.new_T.connect(self.update_all_data)
        self.UpdateWorker.start()

    # =========================================================================
    # UPDATE FUNCTIONS (READING)
    # =========================================================================


    def update_all_data(self, data_list):
        if not isinstance(data_list, list) or len(data_list) < 8:
            return
            
       # 1. Temperature extraction (Index 0 to 4)
        self.parameter_dict['ChannelA_T'] = data_list[0] # Sample
        self.parameter_dict['ChannelB_T'] = data_list[1] # Radiation Shield
        self.parameter_dict['ChannelC_T'] = data_list[2] # Cold Head
        self.parameter_dict['ChannelD_T'] = data_list[3] # Pulse Tube
        self.parameter_dict['ChannelE_T'] = data_list[4] # Compressor Discharge
        
        # 2. Pressure extraction (Index 5 and 6)
        self.parameter_dict['PressureF'] = data_list[5]  # Vacuum Chamber
        self.parameter_dict['PressureG'] = data_list[6]  # He Return
        
        # 3. Compressor status extraction (Index 7)
        self.parameter_dict['OnOff_comp'] = int(data_list[7])

        # 4. Calculation of sample stability (Channel A)
        self.calculate_stability(data_list[0])

    def calculate_stability(self, current_temp):
        """Calculates temperature stability over a rolling window"""
        self.temp_history.append(current_temp)
        if len(self.temp_history) > self.stability_window:
            self.temp_history.pop(0)

        if len(self.temp_history) >= self.stability_window:
            # Calculation of the maximum variation within the window
            temp_range = max(self.temp_history) - min(self.temp_history)
            if temp_range <= self.stability_threshold:
                self.parameter_dict['Stability'] = "Stable"
            else:
                self.parameter_dict['Stability'] = "In progress"  # "In progress"
        else:
            self.parameter_dict['Stability'] = "In progress"  # "In progress"

    # =========================================================================
    # ACTION / COMMAND FUNCTIONS (WRITING)
    # =========================================================================

    def set_temperature_setpoint(self, loop, target_temp):
        """Sends the setpoint value for the active loop"""
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"SOURce:TEMPerature:SPOint {loop}, {target_temp}")
            print(f"Loop {loop} setpoint updated to: {target_temp} K")
            self.parameter_dict['Set_T'] = target_temp
        except Exception as e:
            print(f"Error while sending the setpoint: {e}")


    def set_heater_range(self, loop, range_level):
        """Sets the Heater Range (0=Off, 1=Low, 2=Medium, 3=High)"""
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"SOURCE:HEATer:RANGe {loop}, {range_level}")
            print(f"Loop {loop} Heater Range updated to: {range_level}")
        except Exception as e:
            print(f"Error while sending the Heater Range: {e}")

    def set_pid_parameters(self, loop, p, i, d):
        """Sends the three PID loop parameters to the controller"""
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"SOURce:TEMPerature:PROPortional {loop}, {p}")
            self.Opti.write(f"SOURce:TEMPerature:INTegral {loop}, {i}")
            self.Opti.write(f"SOURce:TEMPerature:DERivative {loop}, {d}")
            print(f"Loop {loop} PID parameters updated: P={p}, I={i}, D={d}")
            self.parameter_dict['Pid_P'] = p
            self.parameter_dict['Pid_I'] = i
            self.parameter_dict['Pid_D'] = d
        except Exception as e:
            print(f"Error while sending the PID parameters: {e}")

    def set_compressor_state(self, state_on):
        """Turns the helium compressor ON (True) or OFF (False)"""
        if not self.is_connected: return
        etat_str = "ON" if state_on else "OFF"
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write(f"CONTrol:COMPressor:STATe {etat_str}")
            print(f"Compressor set to: {etat_str}")
            self.parameter_dict['OnOff_comp'] = 1 if state_on else 0
        except Exception as e:
            print(f"Compressor command error: {e}")

    def reset_compressor_alarm(self):
        """Sends a Reset command to clear compressor alarms"""
        if not self.is_connected: return
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)
            self.Opti.write("CONTrol:COMPressor:RESet")
            print("Alarm reset command sent.")
            self.parameter_dict['Critical_State'] = "OK"
        except Exception as e:
            print(f"Error during alarm reset: {e}")


class PascalWorker(QtCore.QThread):
    new_T = QtCore.pyqtSignal(list)

    def __init__(self, instrument_visa, visa_mutex, is_connected):
        super(PascalWorker, self).__init__()
        self.stop = False
        self.waitTime = 1.0  # 1 second between each cycle
        ...

    def run(self):
        while not self.stop:
            if self.is_connected:
                data = self.read_all_hardware_data()
                if data:
                    self.new_T.emit(data)
            time.sleep(self.waitTime)

    def read_all_hardware_data(self):
        """Queries the device to read all sensors at once"""
        try:
            locker = QtCore.QMutexLocker(self.visa_mutex)    
            
            # 1. Reading the 5 SCPI Temperature Channels
            rep_temp = self.Opti.query("MEASure:TEMPerature? (@1,2,3,4,5)")
            temps_float = [float(t) for t in rep_temp.strip().split(',')]
            
            # 2. Reading the 2 Pressure Gauges
            rep_press = self.Opti.query("MEASure:PRESSure? (@1,2)")
            press_float = [float(p) for p in rep_press.strip().split(',')]
            
            # 3. Reading the compressor status (0 = OFF, 1 = ON)
            rep_comp = self.Opti.query("CONTrol:COMPressor:STATe?")
            comp_state = 1 if "ON" in rep_comp.upper() else 0
            
            locker.unlock()
            
            # Merge all readings into a single list for the signal
            # Index: [0..4] Temperatures, [5..6] Pressions, [7] Compressor Status
            return temps_float + press_float + [comp_state]
            
        except Exception as e:
            # In case of disconnection or timeout, safe/neutral default values are returned
            return [300.0, 300.0, 300.0, 300.0, 300.0, 101300.0, 101300.0, 0]