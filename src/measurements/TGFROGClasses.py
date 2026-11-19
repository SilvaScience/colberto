"""
Measurement class for TG-FROG (transient-grating frequency-resolved optical gating) pulse
characterization. Uses the existing boxcar apparatus: two beams (the "grating" beams) stay at
their own compressed phase, held at zero relative delay, and interfere in a Kerr medium at the
sample position to write a transient grating. The third beam (the "probe") is scanned in delay
via the SLM and diffracts off that grating in the phase-matched boxcar direction. The
spectrometer records the diffracted signal's intensity vs (delay, wavelength) -- a FROG trace.

Note on naming: "grating" is used here for two unrelated things, as it is throughout the rest
of the codebase -- the SLM's diffraction stripe (grating_period, beam.makeGrating()) that
imposes phase on each beam, and the transient (spatial, refractive-index) grating that two of
the beams write in the nonlinear medium. Comments below spell out which is meant where it is not
obvious from context.

For a probe delay tau (fs) and grating beams B, C held at their own current phase (relative
delay 0), the phase-matched TG signal field is E_sig(t, tau) = E_A*(t - tau) * E_B(t) * E_C(t),
i.e. the probe appears conjugated. Retrieval (offline, see samples/retrieval/tgfrog_retrieval.py)
uses pypret's PNPS(pulse, "frog", "tg") process, which expects exactly this convention.
"""

import time
import datetime
import logging

import numpy as np
from numpy.polynomial import Polynomial as P
from PyQt5 import QtCore

logger = logging.getLogger(__name__)


class TGFROGMeasurement(QtCore.QThread):
    """
        Runs a TG-FROG delay scan.

        Signals:
            - sendProgress: float, measurement progress (0-100)
            - sendSpectrum: current background-subtracted spectrum (wavelengths, intensities),
              for a live single-trace display
            - sendBeam: (name, Beam) tuple, so BeamExplorer/DataHandling stay in sync
            - sendTrace: (delay, wavelengths, data) running 2D trace, for the live 2D plot
            - sendTraceData: (name, dict) tuple with the raw trace and metadata, for
              DataHandling.add_calibration
    """

    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeam = QtCore.pyqtSignal(object)
    sendTrace = QtCore.pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    sendTraceData = QtCore.pyqtSignal(tuple)

    def __init__(self, devices, background, grating_period, probe_carrier_wavelength,
                 delay_step, delay_max, delay_min,
                 probeBeamName, gratingBeam1Name, gratingBeam2Name,
                 probeBeam, gratingBeam1, gratingBeam2,
                 spectral_calibration=None, demo=False,
                 demo_fwhm=12e-15, demo_gdd=50e-30, demo_tod=100e-45,
                 demo_noise_level=0.0, demo_seed=0, demo_N=256, demo_dt=2e-15,
                 demo_window_nm=600):
        """
            Initializes the TG-FROG measurement.
            input:
                - devices: the devices dictionnary holding at least a spectrometer and a SLM
                - background: the background to be removed from each spectrum (0 to disable)
                - grating_period: (int) the vertical period (in pixels) of the SLM's phase
                  grating -- unrelated to the transient grating, see module docstring
                - probe_carrier_wavelength: set in the GUI, in nm
                - delay_step, delay_max, delay_min: probe delay scan range, set in the GUI, in fs
                - probeBeamName, gratingBeam1Name, gratingBeam2Name: beam names as set in the GUI
                - probeBeam, gratingBeam1, gratingBeam2: the corresponding Beam objects
                - spectral_calibration: pixel to wavelength calibration (polynomial), shared by
                  all three beams since they share one SLM
                - demo: if True, generate a synthetic trace with pypret instead of using hardware
                - demo_fwhm, demo_gdd, demo_tod: synthetic pulse intensity FWHM (s) and spectral
                  phase Taylor coefficients (s^2, s^3) used to build the demo trace
                - demo_noise_level: fraction of peak trace intensity used as the standard
                  deviation of additive Gaussian noise on the demo trace (0 = clean)
                - demo_seed: RNG seed for reproducible demo traces
                - demo_N, demo_dt: pypret FourierTransform grid size and spacing (s) used to
                  build the demo trace
                - demo_window_nm: width (nm) of the wavelength window kept around
                  probe_carrier_wavelength. pypret's internal FFT frequency grid spans far more
                  bandwidth than any real spectrometer window (dt=2fs alone implies a >1000 nm
                  span), so the full grid is cropped to mimic what a spectrometer would report.
                  Default (600 nm) is wide enough for a clean retrieval; narrowing it towards the
                  ~50-150 nm a real grating gives (see manual/ reports) reproduces the accuracy
                  loss quantified in the Phase 0 physics work -- this is a real effect of
                  insufficient spectral coverage, not a bug.
        """
        super(TGFROGMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.SLM = devices['SLM']

        self.background = background
        self.terminate = False
        self.acquire_measurement = True
        self.delay = np.arange(delay_min, delay_max, delay_step, dtype=int)  # probe delay, fs
        self.intensities = []
        self.isDemo = demo
        self.demo_fwhm = demo_fwhm
        self.demo_gdd = demo_gdd
        self.demo_tod = demo_tod
        self.demo_noise_level = demo_noise_level
        self.demo_seed = demo_seed
        self.demo_N = demo_N
        self.demo_dt = demo_dt
        self.demo_window_nm = demo_window_nm

        self.probeBeamName = probeBeamName
        self.gratingBeam1Name = gratingBeam1Name
        self.gratingBeam2Name = gratingBeam2Name
        self.probeBeam = probeBeam
        self.gratingBeam1 = gratingBeam1
        self.gratingBeam2 = gratingBeam2
        self.probe_carrier_wavelength = probe_carrier_wavelength

        if not self.isDemo:
            self.wls = np.array(self.spectrometer.get_wavelength())
        else:
            self.wls = np.array([])

        if spectral_calibration is None:
            arbitrary_calibration = P(1e-9 * np.array([probe_carrier_wavelength - 100, 1 / 10]))
            for beam in (self.probeBeam, self.gratingBeam1, self.gratingBeam2):
                beam.set_pixelToWavelength(arbitrary_calibration)
            logger.warning('%s Arbitrary spectral calibration used' % datetime.datetime.now())
        else:
            for beam in (self.probeBeam, self.gratingBeam1, self.gratingBeam2):
                beam.set_pixelToWavelength(spectral_calibration)

        for beam in (self.probeBeam, self.gratingBeam1, self.gratingBeam2):
            beam.set_gratingPeriod(grating_period)

        self.trace_data = {
            'delay': self.delay,
            'wavelengths': self.wls,
            'intensities': self.intensities,
            'probe_carrier_wavelength': probe_carrier_wavelength,
            'probe_beam_name': probeBeamName,
            'grating_beam_1_name': gratingBeam1Name,
            'grating_beam_2_name': gratingBeam2Name,
        }

    def run(self):
        logger.info(time.strftime('%H:%M:%S') + ' Begin TG-FROG delay scan')
        try:
            if self.isDemo:
                self._run_demo()
            else:
                self._run_hardware()
            logger.info(time.strftime('%H:%M:%S') + ' Finished')
        except Exception:
            logger.exception('TG-FROG measurement failed')
        finally:
            self.sendProgress.emit(100)
            self.stop()

    def _run_hardware(self):
        """ Holds the two grating beams at their own current (compressed) phase and zero
        relative delay, then scans the probe beam's delay via the SLM, one spectrum per step. """
        self.gratingBeam1.set_currentPhase(
            P(self.gratingBeam1.get_optimalPhase(units_to_return='fs').coef),
            mode='absolute', unit='fs')
        self.gratingBeam2.set_currentPhase(
            P(self.gratingBeam2.get_optimalPhase(units_to_return='fs').coef),
            mode='absolute', unit='fs')
        self.sendBeam.emit((self.gratingBeam1Name, self.gratingBeam1))
        self.sendBeam.emit((self.gratingBeam2Name, self.gratingBeam2))
        grating_image = self.gratingBeam1.makeGrating() + self.gratingBeam2.makeGrating()

        for i in range(len(self.delay)):
            if self.terminate:
                break
            self.probeBeam.set_currentPhase(P([0, self.delay[i]]), mode='relative', unit='fs')
            self.sendBeam.emit((self.probeBeamName, self.probeBeam))
            probe_image = self.probeBeam.makeGrating()

            self.SLM.write_image(grating_image + probe_image)
            self.take_spectrum(i)
            self.intensities.append(self.spec)
            self.sendProgress.emit(i / len(self.delay) * 100)
            self.trace_data['intensities'] = np.array(self.intensities)
            if i >= 1:
                self.sendTrace.emit(self.delay[:i + 1], self.wls, np.array(self.intensities))

        self.sendTraceData.emit((
            f'TGFROG_raw_data_{self.probeBeamName}_{self.gratingBeam1Name}_{self.gratingBeam2Name}',
            self.trace_data))

    def take_spectrum(self, i):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.spec = self.spec - self.background
        self.sendSpectrum.emit(self.wls, self.spec)

    def _run_demo(self):
        """ Builds a synthetic TG-FROG trace with pypret's own forward model (PNPS 'tg' process)
        from a Gaussian pulse with known GDD/TOD, so the acquisition pipeline and GUI can be
        exercised without hardware. Not a substitute for the Phase 0 physics validation. """
        import pypret

        ft = pypret.FourierTransform(self.demo_N, dt=self.demo_dt)
        pulse = pypret.Pulse(ft, self.probe_carrier_wavelength * 1e-9)
        sigma_t = 0.5 * self.demo_fwhm / np.sqrt(np.log(2.0))
        pulse.field = pypret.lib.gaussian(pulse.t, sigma=sigma_t)
        spectral_phase = 0.5 * self.demo_gdd * pulse.w ** 2 + (self.demo_tod / 6.0) * pulse.w ** 3
        pulse.spectrum = pulse.spectrum * np.exp(1j * spectral_phase)

        pnps = pypret.PNPS(pulse, 'frog', 'tg')
        delay_s = self.delay * 1e-15
        Tmn = pnps.calculate(pulse.spectrum, delay_s)
        wls_full_m = pnps.process_wl
        wls_full = wls_full_m * 1e9  # m -> nm

        """ pnps.calculate returns intensity per unit FREQUENCY (see pnps.py's measure()
        docstring), but a real spectrometer reports counts per pixel, i.e. intensity per unit
        WAVELENGTH. The offline retrieval script (samples/retrieval/tgfrog_retrieval.py) applies
        the lambda^2 Jacobian to convert real spectrometer data to the frequency domain pypret
        needs, so undo it here -- otherwise this synthetic trace would double-convert and give a
        badly distorted retrieval (found by testing this demo mode in closed loop against a
        known GDD/TOD; see manual/ reports). """
        inverse_jacobian = 2 * np.pi * 299792458.0 / wls_full_m ** 2
        Tmn = Tmn * inverse_jacobian[np.newaxis, :]

        """ pnps.process_wl spans the whole FFT-conjugate frequency grid (here, >1000 nm around
        the fundamental for demo_dt=2fs), far wider than any real spectrometer window. Crop to a
        band around the probe carrier so the synthetic trace looks like actual spectrometer
        data, matching the ~50-150 nm windows discussed for the real instrument. """
        half_window = self.demo_window_nm / 2
        keep = np.abs(wls_full - self.probe_carrier_wavelength) <= half_window
        wls_cropped = wls_full[keep]
        Tmn_cropped = Tmn[:, keep]
        """ process_wl decreases with increasing frequency index (higher frequency = shorter
        wavelength). Real spectrometers report wavelength ascending by pixel, so sort to match
        and avoid ambiguity in the live plot / retrieval script. """
        sort_idx = np.argsort(wls_cropped)
        self.wls = wls_cropped[sort_idx]
        Tmn = Tmn_cropped[:, sort_idx]

        if self.demo_noise_level > 0:
            rng = np.random.default_rng(self.demo_seed)
            Tmn = Tmn + self.demo_noise_level * Tmn.max() * rng.standard_normal(Tmn.shape)

        for i in range(len(self.delay)):
            if self.terminate:
                break
            self.spec = Tmn[i, :]
            self.intensities.append(self.spec)
            self.sendSpectrum.emit(self.wls, self.spec)
            self.sendProgress.emit(i / len(self.delay) * 100)
            if i >= 1:
                self.sendTrace.emit(self.delay[:i + 1], self.wls, np.array(self.intensities))

        self.trace_data['wavelengths'] = self.wls
        self.trace_data['intensities'] = np.array(self.intensities)
        self.sendTraceData.emit((
            f'TGFROG_raw_data_{self.probeBeamName}_{self.gratingBeam1Name}_{self.gratingBeam2Name}',
            self.trace_data))

    def stop(self):
        self.terminate = True
        logger.info(time.strftime('%H:%M:%S') + ' Request Stop')


class TGFROGRetrievalWorker(QtCore.QThread):
    """
        Runs offline TG-FROG retrieval (COPRA via pypret, samples/retrieval/tgfrog_retrieval.py)
        in a background thread so the GUI stays responsive -- a multi-start retrieval can take
        up to a minute. Wraps that script's functions instead of duplicating them so the GUI
        button and the command-line script can't drift apart.

        Signals:
            - sendResult: dict with trace_error, GD, GDD, TOD (fs, fs^2, fs^3)
            - sendError: str, if retrieval raised an exception
    """
    sendResult = QtCore.pyqtSignal(dict)
    sendError = QtCore.pyqtSignal(str)

    def __init__(self, trace, maxiter=300, n_starts=5):
        """
            input:
                - trace: dict with 'delay' (fs), 'wavelengths' (nm), 'intensities',
                  'probe_carrier_wavelength' (nm) -- the same shape TGFROGMeasurement exports
                - maxiter, n_starts: passed to the retrieval script's retrieve()
        """
        super(TGFROGRetrievalWorker, self).__init__()
        self.trace = trace
        self.maxiter = maxiter
        self.n_starts = n_starts

    def run(self):
        logger.info(time.strftime('%H:%M:%S') + ' Begin TG-FROG retrieval')
        try:
            from samples.retrieval.tgfrog_retrieval import (
                build_measurement, retrieve, extract_taylor_coefficients)
            pulse, pnps, measured = build_measurement(self.trace)
            result = retrieve(pulse, pnps, measured, max_iter=self.maxiter,
                               verbose=False, n_starts=self.n_starts)
            taylor = extract_taylor_coefficients(pulse, result.pulse_retrieved)
            self.sendResult.emit({
                'trace_error': float(result.trace_error),
                'GD': float(taylor[0]),
                'GDD': float(taylor[1]),
                'TOD': float(taylor[2]),
            })
            logger.info(time.strftime('%H:%M:%S') + ' Retrieval finished')
        except Exception as e:
            logger.exception('TG-FROG retrieval failed')
            self.sendError.emit(str(e))
