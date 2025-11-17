# Spatial Light Modulator (SLM)

Colberto uses a Spatial light modulator at its heart to shape pulses in the spectral domain. Here is how it is interfaced.

Controlling the SLM involves three parts:
- The driver [SLM](\ref Slm_Meadowlark_optics.SLM) hosts the DLLs that directly control the SLM and implements them in methods of the SLM class. Commonly used functions are 
    - [create_sdk](\ref Slm_Meadowlark_optics.SLM#create_sdk) to create the software window on a secondary monitor (like the SLM) where the phase image will be displayed and load DLLs
    - [load_lut](\ref Slm_Meadowlark_optics.SLM#load_lut) to load the conversion from grayscale image to voltages to be sent to the SLM
    - [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) to update the image displayed on the SLM
    - [delete_sdk](\ref Slm_Meadowlark_optics.SLM#delete_sdk) to graciously shutdown the driver
- The worker [SLMWorker](\ref SLM.SLMWorker) instantiates the SLM driver in a thread. It constantly checks if a new image should be displayed, what the temperature of the SLM is and shutdown the SLM once the program is closed. It also converts the phase images to grayscale.
    - Signals are defined to communicate the temperature (`slmParamsTemperature`), SLM parameters (`slmParamsSignal`) and the image just displayed (`newImageSignal`) to the interface.
    - Changing the image is done by calling [change_image](\ref SLM.SLMWorker#change_image) This sets the `new_image_available` flag to `True` which is picked up in the loop to display the image and then set to `False`.
        - If a phase image is provided (specified by setting the `imagetype` string to `phase` (default)) the image is converted to a grayscale image by the normalize_phase_image"()" function.
        - this function also converts the 2D image into an RGB image. This is the format required with the current configuration of [write_image](\ref Slm_Meadowlark_optics.SLM#write_image) in [write_image_slm](\ref SLM.SLMWorker#write_image_slm)
        - this function counts the time elapsed since the last displayed image and freezes the thread if not enough time has passed. This wait time can be changed by setting the `target_fps` attribute to the desired frame rate.
- The interface (Slm in SLM.py) instantiates the worker thread. This part ensures communication between the main loop and the worker using:
    - It is instantiated in the main loop by calling its constructor [Slm](\ref SLM.Slm#Slm) and stored in the `devices` dictionnary with the 'SLM' key
    - It starts the SLM worker by calling its constructor [SLMWorker](\ref SLM.SLMWorker#SLMWorker), connecting to its signals to build the parameters display dict to be shown in the UI and starting the thread.
    - The display on the SLM is changed by feeding an image to [write_image](\ref SLM.Slm#write_image). This will eventually trigger the update_image_from_array"()" which will update the internal GUI display of the image in the SLM tab.
        - By default, this method expects a float-64 image with numbers between 0 and 2*pi. However, a raw uint8 image can be provided and will be correctly displayed if the `imagetype` argument is set to `'raw'` instead of `'phase'`.


