# Beam management

At its core, Colberto is a device that generates a complex sequence of pulses distinguished in space (their direction) and time (duration and delay). 

## Location of beam configurations and attributes
Beams are managed by instantiations of the `Beam()` class and stored in `self.DataHandling.beams`, a dictionnary of the `DataHandling` Worker. The keys of this dictionnary represent the beam's label and the associated value is a `Beam` object.The dictionnary can be accessed from `main.py` by calling `self.DataHandling.get_beams()`. It is recommended to use the `set_beam()` method of `DataHandling` to add or modify beams by passing it a tuple of `(BEAMLABEL,BEAMOBJECT)`. 

The beams dictionnary can also be accessed by other worker threads using the `sendBeams` signals and `set_beam` and `get_beams` slots in `DataHandling`.

## Calibrations

General calibrations are stored in the `calibration` dictionnary of `DataHandling`.

Beams are the principal object of calibrations in Colberto through [spatial](calibrations/spatial_calibration.md) and temporal calibrations. The results of these are stored in the `beams` dictionnary in `DataHandling`. These calibrations set their attributes and are required for their temporal manipulation.

## Manipulating beams

Attributes in a Beam object are used to generate a phase grating image that will produce a pulse with the desired properties. The grating is generated using `make_grating` method. This phase grating image can be masked using the `make_mask` (configures the mask) and `set_maskStatus` methods (turns the mask on or off). This can be used to modulate a beam's spectrum.

The beam's pulse can be manipulated using the `set_currentPhase` method relatively or not to the optimal compression phase.

Examples of beam manipulation can be found in the beam sample script in `samples/beamsamples.py