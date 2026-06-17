# Driver Documentation: Optidry 250 (CryoPasqal)

This script provides a PyQt5-based, thread-safe hardware driver for controlling and monitoring an Optidry cryostat system via a serial (PyVISA) interface. The driver uses a two-thread architecture to ensure that the main GUI does not freeze while waiting for hardware responses.

## System Architecture


- CryoPasqal (Main Class): Acts as the primary interface for the application. It stores the state of all device parameters, sends control commands (like setting temperatures or PID values), and calculates stability.

- PascalWorker (Background Thread): A dedicated background thread that continuously polls the cryostat for live sensor readings (temperatures, pressures, compressor state) every second. It uses PyQt5 signals to safely send this data back to the main thread.

## Available Parameters ( parameter_display_dic)

The driver exposes several parameters that can be monitored or controlled:

| Parameter Category | Keys |  Read/Write | Description | 
| ------------------ | ---- |  ---------- | ----------- | 
| Temperature        | ChannelA_T to ChannelE_T | Read |  Live sensor temperatures (Channels 1-5) in Kelvin. | 
| Pressures | PressureF, PressureG | Read | Live sensor pressures (Channels 1-2) in Pascals.  | 
|  Control   |  Set_T, Regulation_Loop | Write |  The target temperature setpoint and the active control loop. | 
|    PID Settings |  Pid_P, Pid_I, Pid_D | Write  |  Proportional, Integral, and Derivative control values. |
|    Compressor |  OnOff_comp | Read/Write  | Compressor state (0 = Off, 1 = On). |
|    Status |  Stability, Critical_State | Read  | Computed system statuses indicating if the temperature is stable and if alarms are triggered. |

## Main Functions (CryoPasqal)

- __init__(port_com): Initializes the parameter dictionaries, opens the PyVISA resource connection to the specified COM port, and starts the PascalWorker background thread.

- set_parameter(parameter, value): A central dispatcher function. When the GUI changes a parameter (like Set_T or Pid_P), this function updates the internal dictionaries and routes the command to the correct hardware control function.

- update_all_data(data_list): A Qt Slot that receives a list of live data from the worker thread, updates the internal state, and triggers the stability calculation.

- calculate_stability(current_temp): Appends the newest ChannelA_T reading to a rolling history. If the temperature fluctuates by less than 0.05 K over the last 30 readings, it marks the system status as "Stable".

- Hardware Control Methods: Functions like set_temperature_setpoint(), set_heater_range(), set_pid_parameters(), and set_compressor_state() send formatted SCPI commands over the VISA connection to alter the physical state of the machine. They use a QMutexLocker to prevent data collisions with the polling thread.