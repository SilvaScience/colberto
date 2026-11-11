# Spatial Light Modulator (SLM)

Colberto uses a Spatial light modulator at its heart to shape pulses in the spectral domain. Here is how it is interfaced. The ribbon shield CAD file can be found in the hardware folder. 

Controlling the SLM involves three parts:
- The driver [SLM](\ref Slm_Meadowlark_optics.SLM) hosts the DLLs that directly control the SLM and implements them in methods of the SLM class. You have to choose the config file and modify the path accordingly in the SLM.py worker. Commonly used functions are 
    - [create_sdk](\ref Slm_Meadowlark_optics.SLM#create_sdk) to create the software window on a secondary monitor (like the SLM) where the phase image will be displayed and load DLLs
    - [load_lut](\ref Slm_Meadowlark_optics.SLM#load_lut) to load the conversion from grayscale image to voltages to be sent to the SLM
    - [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) to update the image displayed on the SLM
    - [delete_sdk](\ref Slm_Meadowlark_optics.SLM#delete_sdk) to graciously shutdown the driver
- The worker [SLMWorker](\ref SLM.SLMWorker) instantiates the SLM driver in a thread. It sleeps until a new image is requested (and wakes up every second to check the temperature of the SLM) and shutdown the SLM once the program is closed. It also converts the phase images to grayscale.
    - Signals are defined to communicate the temperature (`slmParamsTemperature`), SLM parameters (`slmParamsSignal`) and the image just displayed (`newImageSignal`) to the interface.
    - Changing the image is done by calling [change_image](\ref SLM.SLMWorker#change_image) This stores the image, gives it a sequence number (returned by the method) and wakes up the loop, which displays the newest image as soon as the previous write is over. An image requested while another one is being written is displayed right after it, never dropped.
        - If a phase image is provided (specified by setting the `imagetype` string to `phase` (default)) the image is converted to a grayscale image by the normalize_phase_image"()" function.
        - this function also converts the 2D image into an RGB image. This is the format required with the current configuration of [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) in [write_image_slm](\ref SLM.SLMWorker#write_image_slm)
        - the loop makes sure that at least `1/target_fps` seconds (30 Hz by default, set the `target_fps` attribute to change it) separate the end of a write from the start of the next one. An image that arrives after a quiet period is written at once.
    - To be sure that a measurement sees the new pattern, [wait_displayed](\ref SLM.SLMWorker#wait_displayed) blocks the calling thread until a given image is displayed and the liquid crystal had `settleMs` milliseconds to respond. It is used through the `wait` argument of [write_image](\ref SLM.Slm#write_image) (see the interface below).
    - `settleMs` is read in the `SLM0` section of the config file (60 ms if absent). It depends on the SLM, the driver and the site: it has to be measured, for instance with the SLM settling measurement script (`samples/drivers/slm_settling.py`), which reports the time needed before a camera acquisition shows the new pattern.
- The interface (Slm in SLM.py) instantiates the worker thread. This part ensures communication between the main loop and the worker using:
    - It is instantiated in the main loop by calling its constructor [Slm](\ref SLM.Slm#Slm) and stored in the `devices` dictionnary with the 'SLM' key
    - It starts the SLM worker by calling its constructor [SLMWorker](\ref SLM.SLMWorker#SLMWorker), connecting to its signals to build the parameters display dict to be shown in the UI and starting the thread.
    - The display on the SLM is changed by feeding an image to [write_image](\ref SLM.Slm#write_image). This will eventually trigger the update_image_from_array"()" which will update the internal GUI display of the image in the SLM tab.
        - By default, this method expects a float-64 image with numbers between 0 and 2*pi. However, a raw uint8 image can be provided and will be correctly displayed if the `imagetype` argument is set to `'raw'` instead of `'phase'`.
        - By default the method returns immediately. With `wait=True` it returns only once the image is displayed and settled (it returns `False` and logs an error if the image is not displayed within `timeout_s`). The measurements use it before starting a camera acquisition. Never use `wait=True` from the GUI thread: it would freeze the interface.


