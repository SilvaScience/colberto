# Beam management

At its core, Colberto is a device that generates a complex sequence of pulses distinguished in space (their direction) and time (duration and delay). 

## Location of beam configurations and attributes
Beams are managed by instantiations of the `Beam()` class and stored in `self.DataHandling.beams`, a dictionnary of the `DataHandling` Worker. The keys of this dictionnary represent the beam's label and the associated value is a `Beam` object.The dictionnary can be accessed from `main.py` by calling `self.DataHandling.get_beams()`. It is recommended to use the `set_beam()` method of `DataHandling` to add or modify beams by passing it a tuple of `(BEAMLABEL,BEAMOBJECT)`. 

The beams dictionnary can also be accessed by other worker threads using the `sendBeams` signals and `set_beam`, `set_multiple_beams` and `get_beams` slots in `DataHandling`.

## Calibrations

General calibrations are stored in the `calibration` dictionnary of `DataHandling`.

Beams are the principal object of calibrations in Colberto through [spatial](calibrations/spatial_calibration.md) and temporal calibrations. The results of these are stored in the `beams` dictionnary in `DataHandling`. These calibrations set their attributes and are required for their temporal manipulation.

## Manipulating beams

Attributes in a Beam object are used to generate a phase grating image that will produce a pulse with the desired properties. The grating is generated using `make_grating` method. This phase grating image can be masked using the `make_mask` (configures the mask) and `set_maskStatus` methods (turns the mask on or off). This can be used to modulate a beam's spectrum.

The beam's phase profile can be manipulated using the `set_currentPhase` method relatively or not to the optimal compression phase.
Spectral phase profiles are stored in a [Numpy Polynomial objects](https://numpy.org/doc/stable/reference/routines.polynomials.polynomial.html)
When a particular spectral phase profile is more convenient for your application (using compressed pulses), the `set_optimalPhase` and `get_optimalPhase` methods can be called to save this desired phase profile in the beam object. Some methods can return current phase profiles relative to this one.

### Units
Managing the units of phase polynomials can be tricky. The convenience static method `convertPhaseCoeffUnits` can convert the units of phase polynomials and is used extensively in the code.
The polynomials kept as attributes of Beam objects have their units in powers of seconds. However, they are often displayed in powers of fs.

Examples of beam manipulation can be found in the beam sample script in `samples/beamsamples.py

## Beam explorer

The status of all beams is mirrored in the Beam Explorer, implemented in `BeamExplorer.py` and its GUI in `beam_explorer.ui`.
Every time a beam object is emitted from DataHandling, the Beam Explorer gets a copy of those and updates the display accordingly.
All attributes of a beam can be modified from the beam explorer. 
The parameters are update only when the APPLY BEAMS button is pressed.
The Relative checkbox sets wether the coefficients displayed in the Current row of the phase table are relative to the optimal row or not.
A plot shows the phase profile of the beam.
Checking Plot Relative plots only the phase profile applied relative to the optimal phase profile.
Beams can be enabled and disabled by toggling the BEAM ON/OFF button.