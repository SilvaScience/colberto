# Spatial Light Modulator (SLM)

Colberto uses a Spatial light modulator at its heart to shape pulses in the spectral domain. Here is how it is interfaced. The ribbon shield CAD file can be found in the hardware folder. 

Controlling the SLM involves three parts:

- The driver [SLM](\ref Slm_Meadowlark_optics.SLM) hosts the DLLs that directly control the SLM and implements them in methods of the SLM class. It is constructed with the paths of the two Meadowlark DLLs (`cWrapper` and `imageGen`), which the worker reads from the config file. Commonly used functions are 
    - [create_sdk](\ref Slm_Meadowlark_optics.SLM#create_sdk) to create the software window on a secondary monitor (like the SLM) where the phase image will be displayed and load DLLs
    - [load_lut](\ref Slm_Meadowlark_optics.SLM#load_lut) to load the conversion from grayscale image to voltages to be sent to the SLM
    - [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) to update the image displayed on the SLM
    - [normalize_phase_image](\ref Slm_Meadowlark_optics.SLM#normalize_phase_image) a static method converting a float phase image (0 to 2*pi) into the 3-channel uint8 RGB image that `write_image` expects
    - [parameter_slm](\ref Slm_Meadowlark_optics.SLM#parameter_slm) to read back height, width, depth, rgb and is8bit from the hardware
    - [delete_sdk](\ref Slm_Meadowlark_optics.SLM#delete_sdk) to graciously shutdown the driver
    - A 10-bit variant of the driver lives in `Slm_Meadowlark_optics_10bit.py`.
- The worker [SLMWorker](\ref SLM.SLMWorker) instantiates the SLM driver in a thread. It constantly checks if a new image should be displayed and shuts the SLM down once the program is closed. It also converts the phase images to grayscale.
    - The configuration is read from an INI file whose path is hardcoded at the top of `SLMWorker.__init__` (currently `C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\config_UdeM.ini`). Change that path if your installation differs. The file is parsed by `CaseInsensitiveConfig`, a case-insensitive `configparser`, and provides `driverName`, `cWrapper`, `imageGen`, `lutFile`, `rgb`, `isEightBitImage`, `height`, `width`, `depth` and `bytesPerPixel` under the `SLM0` section.
    - `driverName` selects which module in `src/drivers` is imported to build the SLM object, so switching between the 8-bit and 10-bit driver is a config change, not a code change.
    - On startup the worker creates the SDK and loads the LUT named by `lutFile`. Loading a LUT writes it to the SLM's nonvolatile memory, so it only has to be done once; a different LUT can be loaded at run time from `Slm.load_LUT()` (bound to the Load LUT File button, which opens a file dialog when no path is given).
    - Signals are defined to communicate the SLM parameters (`slmParamsSignal`, emitted once at startup with height, width, depth, rgb and is8bit), the temperature (`slmParamsTemperature`), the image just displayed (`imageSLM`, connected to the SLM tab display in `main.py`), an initialization error (`errorSignal`) and the "phase is now shown" flag (`sendFlag`).
    - Note that `get_temperature()` is currently commented out, so the Temperature row of the parameter tree stays at its default value.
    - Changing the image is done by calling [change_image](\ref SLM.SLMWorker#change_image). This converts the image and sets the `new_image_available` flag to `True` which is picked up in the loop to display the image and then set to `False`.
        - If a phase image is provided (specified by setting the `imagetype` string to `phase` (default)) the image is converted to a grayscale RGB image by the driver's `normalize_phase_image"()"` method, which is the format required by [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) in [write_image_slm](\ref SLM.SLMWorker#write_image_slm).
        - The run loop only displays a new image once `frame_duration` has elapsed since the last one, which caps the refresh rate. This wait time can be changed by setting the `target_fps` attribute (30 by default) before the thread is started.
        - `phaseShown` tracks whether the image handed to the SLM has actually been displayed: it is cleared by `write_image`/`change_image` and set again by the driver's `sendFlag` signal once the image has been written. `Slm.check_phaseShown()` exposes it, so a measurement can make sure it is not acquiring on a stale phase pattern. Measurement classes currently wait with a fixed `time.sleep` instead.
- The interface (Slm in SLM.py) instantiates the worker thread. This part ensures communication between the main loop and the worker using:
    - It is instantiated in `Instruments.load_instruments()` by calling its constructor [Slm](\ref SLM.Slm#Slm) and stored in the `devices` dictionnary with the 'SLM' key. If the construction fails, `SLMDemo` is loaded instead and the rest of the program runs unchanged.
    - It starts the SLM worker by calling its constructor [SLMWorker](\ref SLM.SLMWorker#SLMWorker), connecting to its signals to build the parameters display dict to be shown in the UI and starting the thread.
    - The parameters exposed in the tree are `Temperature`, `Height`, `Width`, `Depth`, `rgb`, `is8bit` (all read-only) and `greyscale_val`. `get_height()`, `get_width()`, `get_depth()` and `get_parameters()` are the wrappers used everywhere a Beam has to be sized to the SLM.
    - The display on the SLM is changed by feeding an image to [write_image](\ref SLM.Slm#write_image). The worker then emits `imageSLM`, which updates the internal GUI display of the image in the SLM tab (`SLMDisplay.set_data`).
        - By default, this method expects a float-64 image with numbers between 0 and 2*pi. However, a raw uint8 image can be provided and will be correctly displayed if the `imagetype` argument is set to `'raw'` instead of `'phase'`.

The image displayed is normally the sum of the `makeGrating()` images of every beam, built and emitted by the Beam Explorer when APPLY BEAMS is pressed. See [Beam management in Colberto](beam_management.md).
