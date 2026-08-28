# Driver Documentation: Optidry 250 (CryoPasqal)

`src/drivers/Optidry250.py` provides a PyQt5-based, thread-safe hardware driver for controlling and monitoring an Optidry cryostat system via a serial (PyVISA) interface. The driver uses a two-thread architecture to ensure that the main GUI does not freeze while waiting for hardware responses.

It is loaded by `Instruments.load_instruments()` under the `cryostat` key. If the VISA connection cannot be opened, `CryoDemo` is loaded instead, which mirrors the same parameter names and command API so the rest of the program is unaffected.

## System Architecture

- CryoPasqal (Main Class): Acts as the primary interface for the application. It stores the state of all device parameters, sends control commands (like setting temperatures or PID values), and calculates stability. Class variables `name = 'CryoPasqal'` and `type = 'Cryostat'` are what the GUI tree uses.

- PascalWorker (Background Thread): A dedicated background thread that continuously polls the cryostat for live sensor readings (temperatures, pressures, compressor state) every second (`waitTime`). It uses the PyQt5 signal `new_T` to safely send this data back to the main thread as a list `[T1..T5, P1, P2, comp_state]`.

- CryostatTab (`src/GUI/cryostattab.py`, `cryostattab.ui`): the dedicated tab, added to `main_GUI.ui` as a promoted widget and bound in `main.py`. `set_driver()` binds it to the driver, connects `UpdateWorker.new_T` to `refresh_interface_display` and wires the Apply, Compressor and Reset alarm buttons. The cryostat row of the main parameter tree is read-only, since everything is set from this tab.

## Available Parameters (parameter_display_dict)

The driver exposes several parameters that can be monitored or controlled:

| Parameter Category | Keys |  Read/Write | Description | 
| ------------------ | ---- |  ---------- | ----------- | 
| Temperature        | ChannelA_T to ChannelE_T | Read |  Live sensor temperatures (Channels 1-5) in Kelvin. | 
| Pressures | PressureF, PressureG | Read | Live sensor pressures (Channels 1-2) in Pascals.  | 
|  Control   |  Set_T, Regulation_Loop | Write |  The target temperature setpoint and the active control loop (1 or 2). | 
|    PID Settings |  Pid_P, Pid_I, Pid_D | Write  |  Proportional, Integral, and Derivative control values. |
|    Compressor |  OnOff_comp | Read/Write  | Compressor state (0 = Off, 1 = On). |
|    Status |  Stability, Critical_State | Read  | Computed system statuses indicating if the temperature is stable and if alarms are triggered. |

`parameter_display_dict` holds value, unit, min, max and the read-only flag; the flat `parameter_dict` holds only the values, for fast access from the GUI.

Note that `Critical_State` is not computed from hardware yet: it stays at "OK" and is only reset by `reset_compressor_alarm()` in the demo driver. The heater range is not a tree parameter either -- it is sent straight from the Cryostat tab.

## Main Functions (CryoPasqal)

- `__init__(port_com='COM9')`: Initializes the parameter dictionaries, opens the PyVISA resource connection (115200 baud, 8N1, `\n` terminations, 2 s timeout) to the specified COM port, and starts the PascalWorker background thread. A failed connection is caught and only sets `is_connected = False`, so the object still exists; every command method then returns immediately.

- `set_parameter(parameter, value)`: A central dispatcher function. When the GUI changes a parameter (like `Set_T` or `Pid_P`), this function updates the internal dictionaries and routes the command to the correct hardware control function. `Set_T` and the PID gains are applied to the loop currently held in `Regulation_Loop`.

- `update_all_data(data_list)`: A Qt Slot that receives the list of live data from the worker thread, updates the internal state, and triggers the stability calculation. Lists shorter than 8 entries are ignored.

- `calculate_stability(current_temp)`: Appends the newest `ChannelA_T` reading to a rolling history. If the temperature spread stays within `stability_threshold` (0.05 K) over the last `stability_window` (30) readings, it marks `Stability` as "Stable", otherwise "In progress".

- Hardware Control Methods: `set_temperature_setpoint(loop, target_temp)`, `set_heater_range(loop, range_level)`, `set_pid_parameters(loop, p, i, d)`, `set_compressor_state(state_on)` and `reset_compressor_alarm()` send formatted SCPI commands over the VISA connection to alter the physical state of the machine. They use a `QMutexLocker` on `visa_mutex` to prevent data collisions with the polling thread, which takes the same lock around its queries.
