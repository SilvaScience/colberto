"""
Offline TG-FROG retrieval.

Loads a trace exported from the "Pulse characterization" tab (TGFROGMeasurement, see
src/measurements/TGFROGClasses.py) via the "Save calibration" button, resamples it onto a
pypret PNPS('frog', 'tg') simulation grid, retrieves the pulse with COPRA, and prints GDD/TOD
extracted from the retrieved spectral phase.

Retrieval is deliberately kept out of the live GUI/app (see manual/ reports and the TG-FROG
project memory): this script is meant to be run by hand, against an exported .h5 file, so a
trace can be re-analyzed with different settings without re-running the measurement.

Usage:
    python tgfrog_retrieval.py path/to/calibration.h5
    python tgfrog_retrieval.py path/to/calibration.h5 --probe A --grating1 B --grating2 C
    python tgfrog_retrieval.py --demo --demo-noise 0.05   # synthetic trace, no file needed

Cross-checking the retrieved GDD against the existing chirp-scan compression tool (Delay/Chirp
tabs) is left to the user: read the retrieved GDD this script prints and compare it by eye
against the chirp scan's fitted optimum, rather than this script guessing which calibration
dict key holds that value.
"""

import argparse
import math

import numpy as np
import h5py
import pypret
from pypret.frequencies import convert

C_LIGHT = 299792458.0  # m/s


def load_hdf5_dict(path):
    """ Minimal, dependency-free mirror of main.py's HDF5Helper._recursively_load: reads a
    nested-group HDF5 file (as written by MainWindow.save_calibration) into a nested dict,
    without importing PyQt5/tkinter through main.py. """
    def _recurse(group):
        result = {}
        for key, item in group.items():
            if isinstance(item, h5py.Group):
                result[key] = _recurse(item)
            else:
                data = item[()]
                if isinstance(data, (np.generic, np.bool_)):
                    data = data.item()
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                result[key] = data
        return result
    with h5py.File(path, 'r') as h5f:
        return _recurse(h5f)


def find_trace(calibration_dict, probe=None, grating1=None, grating2=None):
    """ Locates a TGFROG_raw_data_<probe>_<grating1>_<grating2> entry. If the beam names are
    not given, requires that exactly one TG-FROG trace is present (otherwise ambiguous). """
    candidates = [k for k in calibration_dict if k.startswith('TGFROG_raw_data_')]
    if probe is not None:
        wanted = f'TGFROG_raw_data_{probe}_{grating1}_{grating2}'
        if wanted not in candidates:
            raise KeyError(f'{wanted!r} not found. Available traces: {candidates}')
        return calibration_dict[wanted]
    if len(candidates) != 1:
        raise ValueError(
            f'Expected exactly one TG-FROG trace in the file, found {candidates}. '
            'Pass --probe/--grating1/--grating2 to disambiguate.')
    return calibration_dict[candidates[0]]


def build_measurement(trace, N=256, dt=2e-15):
    """
    Converts a raw (delay, wavelength) spectrometer trace into a pypret MeshData resampled onto
    a PNPS('frog', 'tg') simulation grid, ready for Retriever.retrieve().

    Two conversions a raw spectrometer trace needs before it matches pypret's convention
    (Retriever.retrieve's docstring: "data has to be the measured intensity over the frequency,
    not wavelength"):
      - wavelength -> angular frequency, with the lambda^2 Jacobian rescaling: intensity per
        unit wavelength is not the same quantity as intensity per unit frequency, since
        I(omega) domega = I(lambda) dlambda and domega/dlambda = -2 pi c / lambda^2.
      - resampling onto the PNPS instance's own frequency grid (process_w), which
        Retriever.retrieve() requires to match exactly (MeshData.interpolate does this).
    """
    delay_s = np.asarray(trace['delay'], dtype=float) * 1e-15
    wavelengths_m = np.asarray(trace['wavelengths'], dtype=float) * 1e-9
    intensities = np.asarray(trace['intensities'], dtype=float)
    probe_carrier_wavelength_nm = trace['probe_carrier_wavelength']

    omega = convert(wavelengths_m, 'wl', 'om')
    jacobian = wavelengths_m ** 2 / (2 * np.pi * C_LIGHT)
    intensity_per_omega = intensities * jacobian[np.newaxis, :]
    """ Retrieval is invariant to the trace's overall scale (COPRA fits it via its own mu
    parameter) but not robust to an arbitrarily tiny one: the SI-unit lambda^2 Jacobian above
    can push the peak down to ~1e-50 or smaller, which silently breaks convergence (found by
    testing against a synthetic trace with known GDD/TOD -- see samples/retrieval/README or the
    manual/ reports). Normalizing to a sane O(1) scale keeps the physically meaningful
    wavelength-dependent reweighting while avoiding that. """
    if intensity_per_omega.max() > 0:
        intensity_per_omega = intensity_per_omega / intensity_per_omega.max()

    ft = pypret.FourierTransform(N, dt=dt)
    pulse = pypret.Pulse(ft, probe_carrier_wavelength_nm * 1e-9)
    pnps = pypret.PNPS(pulse, 'frog', 'tg')

    measured = pypret.MeshData(intensity_per_omega, delay_s, omega,
                                labels=['delay', 'frequency', 'intensity'])
    measured.interpolate(axis2=pnps.process_w)
    return pulse, pnps, measured


def extract_taylor_coefficients(pulse, spectrum, max_order=3):
    """
    Fits the retrieved spectral phase with a polynomial weighted by spectral amplitude
    (matching the Phase 0 extraction method: an unweighted fit lets noisy, near-zero-amplitude
    wings dominate and corrupts GDD/TOD). Returns Taylor coefficients [GD, GDD, TOD, ...] in
    fs, fs^2, fs^3, ... consistent with the fs convention Beam uses elsewhere in COLBERTo.
    """
    amplitude = np.abs(spectrum)
    phase = np.unwrap(np.angle(spectrum))
    weights = amplitude / amplitude.max()
    w_fs = pulse.w * 1e-15  # rad/fs
    coef_descending = np.polyfit(w_fs, phase, deg=max_order, w=weights)
    coef_ascending = coef_descending[::-1]
    return [coef_ascending[n] * math.factorial(n) for n in range(1, max_order + 1)]


def generate_demo_trace(probe_carrier_wavelength=800.0, fwhm=12e-15, gdd=50e-30, tod=100e-45,
                         noise_level=0.02, seed=0, delay_min=-200, delay_max=200, delay_step=2,
                         demo_window_nm=600, N=256, dt=2e-15):
    """
    Builds a synthetic TG-FROG trace with known GDD/TOD, in the same dict shape TGFROGMeasurement
    exports. Kept independent from TGFROGMeasurement._run_demo (which is the same physics) so
    this script has no PyQt5 import-time dependency and can run outside the COLBERTo app.
    """
    delay = np.arange(delay_min, delay_max, delay_step, dtype=int)
    ft = pypret.FourierTransform(N, dt=dt)
    pulse = pypret.Pulse(ft, probe_carrier_wavelength * 1e-9)
    sigma_t = 0.5 * fwhm / np.sqrt(np.log(2.0))
    pulse.field = pypret.lib.gaussian(pulse.t, sigma=sigma_t)
    spectral_phase = 0.5 * gdd * pulse.w ** 2 + (tod / 6.0) * pulse.w ** 3
    pulse.spectrum = pulse.spectrum * np.exp(1j * spectral_phase)

    pnps = pypret.PNPS(pulse, 'frog', 'tg')
    Tmn = pnps.calculate(pulse.spectrum, delay * 1e-15)
    wls_full_m = pnps.process_wl
    wls_full = wls_full_m * 1e9

    """ pnps.calculate returns intensity per unit FREQUENCY (see pnps.py's measure() docstring),
    but a real spectrometer reports counts per pixel, i.e. intensity per unit WAVELENGTH.
    build_measurement() applies the lambda^2 Jacobian to convert real spectrometer data to the
    frequency domain pypret retrieval needs; apply its inverse here so this synthetic trace is a
    faithful stand-in for what hardware would actually report, instead of double-converting. """
    inverse_jacobian = 2 * np.pi * C_LIGHT / wls_full_m ** 2
    Tmn = Tmn * inverse_jacobian[np.newaxis, :]

    half_window = demo_window_nm / 2
    keep = np.abs(wls_full - probe_carrier_wavelength) <= half_window
    wls_cropped = wls_full[keep]
    Tmn_cropped = Tmn[:, keep]
    sort_idx = np.argsort(wls_cropped)
    wls = wls_cropped[sort_idx]
    Tmn = Tmn_cropped[:, sort_idx]

    if noise_level > 0:
        rng = np.random.default_rng(seed)
        Tmn = Tmn + noise_level * Tmn.max() * rng.standard_normal(Tmn.shape)

    print(f'Demo ground truth: GDD = {gdd * 1e30:.2f} fs^2, TOD = {tod * 1e45:.2f} fs^3, '
          f'noise level = {noise_level:.3f}')
    return {
        'delay': delay,
        'wavelengths': wls,
        'intensities': Tmn,
        'probe_carrier_wavelength': probe_carrier_wavelength,
    }


def retrieve(pulse, pnps, measured, max_iter=300, verbose=True, n_starts=5):
    """
    Runs COPRA from n_starts independent random initial guesses and keeps the result with the
    lowest trace error. A single attempt can land in a local minimum -- pypret's own reference
    benchmarking script (scripts/benchmarking.py) does the same (repeat=10 by default) for
    exactly this reason; found necessary here too by testing against a synthetic trace with
    known GDD/TOD and noise, where a single attempt occasionally converged to the wrong GDD.
    """
    ret = pypret.Retriever(pnps, 'copra', verbose=verbose, maxiter=max_iter)
    best_result = None
    for i in range(n_starts):
        pypret.random_gaussian(pulse, 50e-15, 0.3 * np.pi)
        ret.retrieve(measured, pulse.spectrum)
        result = ret.result(pulse.spectrum)
        if verbose:
            print(f'  attempt {i + 1}/{n_starts}: trace error = {result.trace_error:.4e}')
        if best_result is None or result.trace_error < best_result.trace_error:
            best_result = result
    return best_result


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', nargs='?', help='HDF5 file saved with "Save calibration"')
    parser.add_argument('--probe', help='Probe beam name, if the file has more than one trace')
    parser.add_argument('--grating1', help='Grating beam 1 name')
    parser.add_argument('--grating2', help='Grating beam 2 name')
    parser.add_argument('--demo', action='store_true',
                         help='Run entirely on a synthetic trace, no file needed')
    parser.add_argument('--demo-noise', type=float, default=0.02,
                         help='Fraction of peak intensity used as demo trace noise std-dev')
    parser.add_argument('--maxiter', type=int, default=300)
    parser.add_argument('--n-starts', type=int, default=5,
                         help='Independent random initial guesses; keeps the best trace error')
    parser.add_argument('--quiet', action='store_true', help='Suppress per-iteration output')
    args = parser.parse_args()

    if args.demo:
        trace = generate_demo_trace(noise_level=args.demo_noise)
    else:
        if not args.path:
            parser.error('path is required unless --demo is given')
        data = load_hdf5_dict(args.path)
        calibration = data.get('calibration', data)
        trace = find_trace(calibration, args.probe, args.grating1, args.grating2)

    pulse, pnps, measured = build_measurement(trace)
    result = retrieve(pulse, pnps, measured, max_iter=args.maxiter, verbose=not args.quiet,
                       n_starts=args.n_starts)

    taylor = extract_taylor_coefficients(pulse, result.pulse_retrieved)
    print()
    print(f"Trace error G' = {result.trace_error:.4e}")
    print('Retrieved spectral phase, Taylor-expanded around the probe carrier:')
    for label, unit, value in zip(['GD', 'GDD', 'TOD'], ['fs', 'fs^2', 'fs^3'], taylor):
        print(f'  {label:4s} = {value:12.4f} {unit}')
    print()
    print('Compare GDD above by eye against the chirp-scan (Delay/Chirp tabs) fitted optimum '
          'if one was taken -- not done automatically, see module docstring.')


if __name__ == '__main__':
    main()
