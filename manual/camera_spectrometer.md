# Cameras, spectrometer and monochromator

## Devices and where they are declared

Everything is instantiated in `src/drivers/Instruments.py`, in `load_instruments()`, which is where you add or remove devices. It returns two dictionnaries:

- `devices`: the devices addressed by role and shown in the parameter tree (`cryostat`, `SLM`, `Monochrom` and the currently active `spectrometer`).
- `spectrometers`: every detector that could be connected, keyed by name (`Stresing`, `Pixis`, `Ocean`, `Demo`). Each one is attempted in a `try/except`, so a camera that is not plugged in is simply absent from the dictionnary instead of preventing startup.

The monochromator (`SpectraPro2300i`, or `SpectraPro2300iDemo` when the hardware does not answer) is a device of its own. It is built with a `grating_params` dictionnary holding one set of grating/geometry constants per camera (`Stresing` and `Pixis`), since the pixel size and the number of pixels differ. Cameras are then attached to it with `camera.attach_to_monochromator(Monochrom)`: this stores the monochromator on the camera, sets the camera's `type` to `'Spectrometer'` and copies the grating parameters matching that camera into `hardware_params`. In other words the camera holds the reference to the monochromator, not the other way around, and the wavelength axis of a camera comes from the monochromator's parameters for that camera.

The default detector chosen at startup is Ocean, then Stresing, then Demo.

## Switching camera

On the main panel, top right, a `spec_selection_comboBox` lists the connected detectors. Selecting another camera calls `on_spectrometer_changed`, which:

- points `devices['spectrometer']` at the new camera and updates `spec_length`;
- calls `DataHandling.update_spec_length()` and `DataHandling.change_spectrometer()` so the spectrum, background and wavelength buffers are resized to the new sensor (1D or 2D);
- rebuilds the parameter tree, since the number of parameters differs between cameras;
- reconnects the Camera display and the Acquisition panel to the new camera.

DataHandling is **not** re-instantiated any more. It keeps its beams, its calibrations and its connection to the Beam Explorer across a camera change. Only the buffers tied to the sensor are reset: in particular the background is dropped (`has_background` goes back to `False`) because a background belongs to the detector it was taken on, and a warning is logged when that happens.

## Spectrum View tab

The tab is assembled in code in `main.py` rather than in `main_GUI.ui`, because the `.ui` file merges badly between contributors. It holds, from top to bottom:

- `AcquisitionSettings`: trigger and timing controls. Rather than the raw `Scan_Trig`/`Block_Trig` registers, it exposes the three setups actually used -- the board on its own timer (continuous), one readout per laser pulse (external) and blocks gated by a chopper -- and derives `sti`/`bti` from that through the camera's `set_acquisition_mode()`. Timers are entered with a unit and the resulting rate and total acquisition time are displayed. The monochromator settings (central wavelength, grating, mirror) are also applied from this panel. Cameras without `set_acquisition_mode()` simply get a disabled panel.
- `CameraDisplay`: the live 2D frame for cameras exposing `set_binned_roi()`/`set_full_frame()`. The readout region can be dragged or typed; applying it changes the number of summed rows and therefore the count scale, so the spectrum plots are cleared (`roi_applied` -> `readout_region_changed`).
- `SpectrometerPlot`: the 1D spectrum. A second copy of that plot is inserted as its own `Spectrum` tab, fed the same data, so it can be read from across the room without the controls.

The spectrometer row of the parameter tree is read-only (like the cryostat), since its settings are edited in the Acquisition panel; `spectrometer_parameter_changed` refreshes the tree after the panel has written to the driver.
