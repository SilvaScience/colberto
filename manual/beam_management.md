# Beam management

At its core, Colberto is a device that generates a complex sequence of pulses distinguished in space (their direction) and time (duration and delay). 

## Location of beam configurations and attributes
Beams are managed by instantiations of the `Beam()` class (`src/compute/beams.py`) and stored in `self.DataHandling.beams`, a dictionnary of the `DataHandling` Worker. The keys of this dictionnary represent the beam's label and the associated value is a `Beam` object. The dictionnary can be accessed from `main.py` by calling `self.DataHandling.get_beams()`. It is recommended to use the `set_beam()` method of `DataHandling` to add or modify beams by passing it a tuple of `(BEAMLABEL,BEAMOBJECT)`. 

The beams dictionnary can also be accessed by other worker threads using the `sendBeams` signal and the `set_beam`, `set_multiple_beams` and `get_beams` slots in `DataHandling`. Both `set_beam` and `set_multiple_beams` call `get_beams` right after updating, so the beams are emitted as soon as they change.

A `Beam` is constructed from the SLM geometry only: `Beam(SLMWidth,SLMHeight)`, typically `Beam(self.devices['SLM'].get_width(),self.devices['SLM'].get_height())`.

## Saving and loading beams

Beams are serialised to HDF5 alongside the calibrations with the `beam_to_dict` static method and rebuilt with `dict_to_beam(beam_dict, beam_class, slm_width, slm_height)`. Numpy Polynomial attributes (`optimalPhasePolynomial`, `currentPhasePolynomial`, `pixelToWavelength`) are stored as `{'_type':'Polynomial','coef':[...]}`. This is what the save/load calibration buttons of `main.py` use.

## Calibrations

General calibrations are stored in the `calibration` dictionnary of `DataHandling`, filled through `add_calibration((name,value))`.

Beams are the principal object of calibrations in Colberto through [spatial](calibrations/spatial_calibration.md) and [temporal](calibrations/temporal_calibration.md) calibrations. The results of these are stored in the `beams` dictionnary in `DataHandling`. These calibrations set their attributes and are required for their temporal manipulation.

## Manipulating beams

Attributes in a Beam object are used to generate a phase grating image that will produce a pulse with the desired properties. The grating is generated using the `makeGrating` method (a sawtooth pattern, `generate_1Dgrating`). A binary variant, `makeStripes` (`generate_1Dstripes`, a square pattern), is used by the LUT calibration. Both call `make_mask` internally before building the image, so the mask always matches the current delimiters and beam status.

The image can be masked using `make_mask` (configures the mask from the vertical and horizontal delimiters) and `set_maskStatus` methods (turns the mask on or off). This can be used to modulate a beam's spectrum. `set_beamStatus(False)` zeroes the mask entirely, which turns the beam off.

The beam's phase profile can be manipulated using the `set_currentPhase` method relatively or not to the optimal compression phase.
Spectral phase profiles are stored in [Numpy Polynomial objects](https://numpy.org/doc/stable/reference/routines.polynomials.polynomial.html)
When a particular spectral phase profile is more convenient for your application (using compressed pulses), the `set_optimalPhase` and `get_optimalPhase` methods can be called to save this desired phase profile in the beam object. Some methods can return current phase profiles relative to this one.

Whether the current phase is interpreted relatively to the optimal phase or not is a property of the beam, set with `set_current_phase_mode('relative'|'absolute')` and read with `get_current_phase_mode()`. `set_currentPhase` and `get_currentPhase` use that mode unless a `mode` argument is passed explicitly. `set_currentPhase_optimal()` copies the optimal phase into the current phase.

Two carrier waves are kept per beam and both are used when the phase is sampled: the compression carrier (`set_compressionCarrierWave`/`get_compressionCarrier`) is the reference for every phase order, and the delay carrier (`set_delayCarrierWave`/`get_delayCarrier`) is the reference used for the linear (group delay) term only. `get_sampledCurrentPhase` splits the polynomial accordingly before evaluating it.

Examples of beam manipulation can be found in the beam sample script `samples/compute/beamssample.py`.

### Units
Managing the units of phase polynomials can be tricky. The convenience static method `convertPhaseCoeffUnits` can convert the units of phase polynomials and is used extensively in the code. It only handles `'s'` and `'fs'`.
The polynomials kept as attributes of Beam objects have their units in powers of seconds. However, they are often displayed in powers of fs.

### Taylor prefactors
Phase coefficients are stored *without* the 1/n! Taylor prefactor. The static method `TaylorPrefactor(phasePolynomial, TaylorPrefactorFlag)` multiplies (`'add'`) or divides (`'remove'`) the coefficients by 1/n!, and is available as the `TaylorPrefactorFlag` argument of `set_optimalPhase`, `get_optimalPhase`, `set_currentPhase` and `get_currentPhase`. `get_sampledCurrentPhase` calls it with `'add'`, so the phase actually sent to the SLM does include the prefactors.

## Beam explorer

The status of all beams is mirrored in the Beam Explorer, implemented in `BeamExplorer.py` and its GUI in `beam_explorer.ui`.
Every time a beam object is emitted from DataHandling (`sendBeams` -> `receive_beams`), the Beam Explorer gets a copy of those and updates the display accordingly.
All attributes of a beam can be modified from the beam explorer. 
The parameters are updated only when the APPLY BEAMS button is pressed. That button then emits two signals: `beams_changed` (connected to `DataHandling.set_multiple_beams`) and `phase_image`, the sum of the `makeGrating()` images of every beam, connected to `Slm.write_image`. So pressing APPLY BEAMS is what pushes the new phase image to the SLM.

IMPORTANT NOTE: the parameters in Beam Explorer correspond to the phase order:
    - CEP :         Carrier-envelope phase
    - GD (fs) :     Group delay 
    - GDD (fs^2) :  Group delay dispersion
    - TOD (fs^3) :  Third-order dispersion
    - FOD (fs^4) :  Fourth-order dispersion
    - HOD (fs^H) :  Higher-order dispersion, 5OD (fs^5), 6OD (fs^6), etc.
The number of columns of the phase table follows the number of coefficients of the beam's optimal phase polynomial, and the headers past FOD are generated automatically.
The Taylor series prefactors 1/n! ARE NOT included in those phase parameters. However, when `makeGrating` is used, the SLM receives the right phase including the prefactors. 
The Relative checkbox sets whether the coefficients displayed in the Current row of the phase table are relative to the optimal row or not; toggling it converts the displayed values and sets the beam's phase mode when APPLY BEAMS is pressed.
A plot shows the phase profile of the beam.
Checking Plot Relative plots only the phase profile applied relative to the optimal phase profile.
`Clear optimal` and `Clear current` zero the optimal and current phase coefficients respectively, keeping the same number of orders.
Beams can be enabled and disabled by toggling the BEAM ON/OFF button.
