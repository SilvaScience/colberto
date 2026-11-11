#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLM latency / settling measurement, using a camera of the setup (Pixis or Stresing) as a time-resolved detector
("method A"). No extra hardware is needed: the light diffracted by the SLM must reach the camera, exactly as in
the spatial calibration.

What it does
------------
The camera acquires a fast series of short frames ("scans") and *all* of them are kept (the drivers normally average
or keep a single one). The SLM pattern is changed and the series shows when the camera actually sees the new pattern.
  --camera pixis    PICam through pylablib, sequence mode, vertical binning of the signal band into one row (as the
                    application does), short exposure, shutter held open (see --shutter). The frame period is
                    limited by the readout (read from the camera and from the frame time stamps, printed at start).
  --camera stresing continuous mode of the Stresing board, one scan every --stimer-us (default 1 ms).

Two experiments are run for every transition (see TRANSITIONS):

1. "real flow" sweep: reproduces what the measurement classes do, i.e. SLM.write_image(after) immediately followed
   by the camera acquisition, but with a controllable pause `delta` (ms) between the two. For every delta the scan
   index at which the spectrum stops changing (`settle_idx`) is found. Scans after the first `first_valid` ones that
   are still changing are "stale". The smallest delta without stale scans is the pause to insert before the camera
   call. The *application-equivalent error* tells what a measurement taken like the application does (one frame of
   --app-exposure-ms for the Pixis, scans 4..9 of 10 ms for the Stresing) would contain: the relative distance
   between the average of the scans of that window and the final spectrum; it must stay below --app-tolerance.
2. "prestart": the camera is started first and write_image() is called `--prestart-delay-ms` later, from the main
   thread. The scans then show the pattern before, during and after the change, which gives the onset and the
   transition duration (onset -> settled). That duration does not depend on when the camera really starts
   integrating. `l_minus_c_ms` = onset time seen by the camera minus the time of the write call = L - c, where L is
   the SLM latency and c the unknown delay between the camera call and its first scan: it is not the SLM latency
   alone (c needs a second, independent timing reference, e.g. a photodiode).

The time resolution is the frame period of the camera: a 100 kHz Pixis readout (about 10 ms per frame) resolves a
60 Hz SLM (16.7 ms) only barely; a 2 MHz readout is much better. The period is printed at start and used for all times.

The software chain of Slm.write_image (call, queued, worker pick-up, driver in/out, flag) is time-stamped too, so
that the share due to our own code (0-33 ms worker gate, waitKey(30), ...) can be separated from the display + liquid
crystal share.

Phase-only transitions (cep_pi, gd_10fs) do not change the diffracted intensity once settled. They can only be seen
if the liquid crystal produces an intensity transient while it rewrites the pattern (an assumption to be checked on
the output). The script says so when no transient is detected.

Usage (from the repository root, laser on, SLM and camera connected, application closed):
    python samples/drivers/slm_settling.py --camera pixis --transitions onoff rows10 cep_pi --plot
Without hardware, to check the analysis chain:
    python samples/drivers/slm_settling.py --simulate --camera pixis --rest-s 0.05 --repeats 2 --prestart-repeats 2

Results (HDF5 with binned scans, summary.txt, optional PNG) are written to --out/<timestamp>/ .
"""

import argparse
import ctypes
import datetime
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / 'src'):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

TRANSITIONS = ('onoff', 'cep_pi', 'rows10', 'gd_10fs')
STRESING_PIXEL_SLICE = slice(13, -1)   # same trimming as StresingCamera.get_intensities
SATURATION = 65000
MIN_SCANS = 40


# ----------------------------------------------------------------------------------------------------------------------
# Analysis (pure numpy)
# ----------------------------------------------------------------------------------------------------------------------
def bin_pixels(scans, k):
    """ Averages groups of k adjacent pixels along the last axis (to keep the saved files small). """
    n = (scans.shape[-1] // k) * k
    return scans[..., :n].reshape(*scans.shape[:-1], n // k, k).mean(axis=-1)


def steady_state(scans, first_valid):
    """ Median spectrum of an acquisition taken long after a pattern change. """
    return np.median(scans[first_valid:], axis=0)


def distance(scans, ref, mask):
    """ L2 distance, over the masked pixels, between every scan and a reference spectrum. """
    return np.linalg.norm((scans - ref)[:, mask], axis=1)


def last_run_end(flags, start):
    """ Index just after the last pair of consecutive True values at or after `start` (`start` if none).
        Requiring two consecutive scans keeps a single noisy scan from moving the result. """
    f = np.asarray(flags[start:], bool)
    pair = f[:-1] & f[1:]
    idx = np.nonzero(pair)[0]
    return int(start + idx[-1] + 2) if idx.size else int(start)


def first_run_start(flags, start):
    """ Index of the first pair of consecutive True values at or after `start`, or None. """
    f = np.asarray(flags[start:], bool)
    pair = f[:-1] & f[1:]
    idx = np.nonzero(pair)[0]
    return int(start + idx[0]) if idx.size else None


def analyze_real(scans, s_before, mask, first_valid, tail_frac=0.25, nsigma=4.0, floor_frac=0.02):
    """
        Finds when the spectrum stops changing in an acquisition that started after the SLM write call.
        input:
            - scans (nd.array): (nos, npix) all the scans of one acquisition
            - s_before (nd.array): steady spectrum of the pattern that was displayed before the change
            - mask (nd.array of bool): pixels carrying the signal
            - first_valid (int): number of leading scans that are ignored (the Stresing driver discards 4)
        output (dict):
            - settle_idx: first scan index after which the spectrum stays within the noise (or 2 % of the
              before/after difference, whichever is larger) of the final spectrum
            - stale: number of scans at or after first_valid that are still changing
            - d: distance to the final spectrum for every scan
            - contrast_snr: distance between the before and after steady spectra over the typical distance of a
              single scan to the final spectrum (about 0.2 when nothing changes); values below 3 mean that the
              change is hardly visible in intensity
            - tail_ok: False if the last quarter of the acquisition is still drifting
    """
    n = len(scans)
    tail0 = max(int(n * (1 - tail_frac)), first_valid + 4)
    s_final = np.median(scans[tail0:], axis=0)
    d = distance(scans, s_final, mask)
    tail = d[tail0:]
    mu, sd = float(tail.mean()), float(tail.std())
    half = len(tail) // 2
    tail_ok = abs(tail[:half].mean() - tail[half:].mean()) <= 3 * max(sd, 1e-12)
    d_ref = float(np.linalg.norm((s_before - s_final)[mask]))
    thr = max(mu + nsigma * sd, floor_frac * d_ref)
    settle = last_run_end(d > thr, first_valid)
    return dict(settle_idx=settle, stale=int(settle - first_valid), d=d, thr=float(thr), d_ref=d_ref,
                noise=sd, contrast_snr=d_ref / max(mu, 1e-12), tail_ok=bool(tail_ok), s_final=s_final)


def app_window_error(scans, res, mask, scan_ms, start_ms, end_ms):
    """
        Relative error that a measurement made like the application would contain: distance between the average of
        the scans lying in [start_ms, end_ms] after the camera start and the final spectrum, over the distance between
        the final and the previous steady spectra. None if the window does not fit in the acquisition.
    """
    i0 = int(round(start_ms / scan_ms))
    i1 = max(int(round(end_ms / scan_ms)), i0 + 1)
    if i1 > len(scans):
        return None
    average = scans[i0:i1].mean(axis=0)
    return float(np.linalg.norm((average - res['s_final'])[mask]) / max(res['d_ref'], 1e-12))


def analyze_prestart(scans, delay_ms, scan_us, mask, first_valid, nsigma=5.0):
    """
        Finds onset and settling in an acquisition that was started BEFORE the SLM write call.
        The head of the acquisition (before half of the expected write position) is the 'before' reference.
        output (dict): onset_idx (None if no change was detected), settle_idx, duration_scans, ...
    """
    k_delay = int(delay_ms * 1000 / scan_us)
    head_end = max(first_valid + 5, k_delay // 2)
    s_before = np.median(scans[first_valid:head_end], axis=0)
    res = analyze_real(scans, s_before, mask, max(first_valid, head_end))
    d_before = distance(scans, s_before, mask)
    head = d_before[first_valid:head_end]
    thr_on = max(head.mean() + nsigma * head.std(), 0.02 * res['d_ref'])
    onset = first_run_start(d_before > thr_on, head_end)
    out = dict(res)
    out.update(onset_idx=onset, head_end=head_end, d_before=d_before, thr_on=float(thr_on))
    out['duration_scans'] = None if onset is None else max(res['settle_idx'] - onset, 0)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Patterns
# ----------------------------------------------------------------------------------------------------------------------
def build_images(width, height, period):
    """ Returns {transition: (image_a, image_b)}. Images are phase images (rad) as given to SLM.write_image. """
    from compute.beams import Beam
    from numpy.polynomial import Polynomial as P

    def grating(vertical=None, phase=None):
        beam = Beam(width, height)
        beam.set_gratingPeriod(period)
        beam.set_gratingAmplitude(1)
        if vertical is not None:
            beam.set_beamVerticalDelimiters(vertical)
        if phase is not None:
            beam.set_currentPhase(P(phase), mode='relative', unit='fs')
        return beam.makeGrating()

    full = grating()
    return {
        'onoff': (np.zeros((height, width)), full),
        'cep_pi': (full, grating(phase=[np.pi])),
        'rows10': (grating(vertical=[0, height // 2]), grating(vertical=[0, height // 2 + 10])),
        'gd_10fs': (full, grating(phase=[0, 10])),
    }


# ----------------------------------------------------------------------------------------------------------------------
# Rigs: real hardware and simulation share the same small interface
#   width, height, nos, scan_us, first_valid, last_call_s, events,
#   write(img), acquire() -> (nos, npix), sleep(s), close()
# ----------------------------------------------------------------------------------------------------------------------
def nos_for_window(args, scan_us):
    """ Number of scans so that the acquisition lasts --window-ms (or --nos if given). """
    if args.nos:
        return int(args.nos)
    return max(int(np.ceil(args.window_ms * 1000.0 / scan_us)), MIN_SCANS)


class HardwareRig:
    """ Application SLM driver (Slm) driven from this script; the camera part is added by the subclasses. """

    def __init__(self, args):
        from PyQt5 import QtCore
        self.app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication(sys.argv[:1])
        from drivers.SLM import Slm
        self.first_valid = args.first_valid
        self.events = []
        self.last_call_s = 0.0
        print('Starting the SLM ...')
        self.slm = Slm()
        # SLM size arrives through a signal that needs the Qt event loop
        self._wait_for(lambda: self.slm.get_width() > 0 and self.slm.get_height() > 0, 30, 'SLM parameters')
        self.width, self.height = int(self.slm.get_width()), int(self.slm.get_height())
        self._wait_for(lambda: self.slm.slm_worker.slm is not None, 30, 'SLM driver')
        if not args.no_trace:
            self._install_trace()

    def _wait_for(self, condition, timeout_s, what):
        deadline = time.monotonic() + timeout_s
        while not condition():
            if time.monotonic() > deadline:
                raise TimeoutError('Timed out waiting for: ' + what)
            self.app.processEvents()
            time.sleep(0.01)

    def _install_trace(self):
        """ Time-stamps the stages of the SLM write chain by wrapping instance methods (the driver is not edited). """
        stamp = lambda name: self.events.append((name, time.perf_counter()))
        slm, worker = self.slm, self.slm.slm_worker

        original_write = slm.write_image

        def write_image(image, imagetype='phase'):
            stamp('call')
            result = original_write(image, imagetype)
            stamp('queued')
            return result
        slm.write_image = write_image

        original_show = worker.write_image_slm

        def write_image_slm():
            stamp('worker_pickup')
            result = original_show()
            stamp('worker_done')
            return result
        worker.write_image_slm = write_image_slm

        driver = worker.slm
        original_driver_write = driver.write_image

        def driver_write(image):
            stamp('driver_in')
            result = original_driver_write(image)
            stamp('driver_out')
            return result
        driver.write_image = driver_write

        worker.sendFlag.connect(lambda shown: stamp('flag_main_thread'))

    def write(self, image):
        self.slm.write_image(image)

    def sleep(self, seconds):
        """ Sleeps while keeping the Qt event loop alive (signals from the SLM threads are delivered here). """
        deadline = time.perf_counter() + seconds
        while True:
            self.app.processEvents()
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return
            time.sleep(min(0.0005, remaining))

    def close_camera(self):
        pass

    def close(self):
        try:
            self.close_camera()
        except Exception as error:
            print('Could not close the camera:', error)
        try:
            self.write(np.zeros((self.height, self.width)))
            self.sleep(0.5)
        except Exception as error:
            print('Could not blank the SLM:', error)
        try:
            self.slm.slm_worker.terminate = True   # SLMWorker.run loops on this attribute
            self.slm.slm_worker.wait(2000)
        except Exception:
            pass
        try:
            import cv2
            cv2.destroyAllWindows()
        except Exception:
            pass


class StresingRig(HardwareRig):
    """ Slm + StresingCamera from the application drivers. """

    def __init__(self, args):
        super().__init__(args)
        from drivers import StresingDriver as sd
        from drivers.Stresing import StresingCamera, CONTINUOUS
        self.sd = sd
        print('Starting the Stresing camera ...')
        self.cam = StresingCamera(dict(pixel_size_mm=24e-3, num_pixels=1010, calibrated=True,
                                       calibrationThirdOrder=-3e-5, calibrationSlope=0.9891,
                                       calibrationOffset=-51.163))
        self.scan_us = float(args.stimer_us)
        self.nos = nos_for_window(args, self.scan_us)
        self.cam.set_acquisition_mode(CONTINUOUS, scan_interval_us=args.stimer_us,
                                      block_interval_us=args.block_interval_us)
        self.cam.set_parameter('No_Sample', self.nos)
        self.cam.set_parameter('No_Block', 1)

    def acquire(self):
        """ One blocking acquisition returning ALL scans, same DLL sequence as StresingDriver.measure. """
        cam, sd = self.cam, self.sd
        if sd.measurement_running(cam):
            sd.abort_measure(cam)
        self._check(cam.dll.DLLCloseShutter(cam.drvno))
        t0 = time.perf_counter()
        self._check(cam.dll.DLLStartMeasurement_blocking())
        self.last_call_s = time.perf_counter() - t0
        settings = cam.settings
        npix = settings.camera_settings[cam.drvno].PIXEL
        nos, nob = settings.nos, settings.nob
        buffer = (ctypes.c_uint16 * (npix * nos * settings.camera_settings[cam.drvno].CAMCNT * nob))(0)
        self._check(cam.dll.DLLCopyAllData(cam.drvno, ctypes.pointer(buffer)))
        self._check(cam.dll.DLLOpenShutter(cam.drvno))
        arr = np.ctypeslib.as_array(buffer).reshape(nob, nos, npix)
        return np.array(arr[0, :, STRESING_PIXEL_SLICE][:, ::-1], dtype=np.float32)

    def _check(self, status):
        if status != 0:
            raise RuntimeError(self.cam.dll.DLLConvertErrorCodeToMsg(status))

    def close_camera(self):
        self.sd.exit(self.cam)


class PixisRig(HardwareRig):
    """ Slm + PICam camera (Pixis) driven through pylablib, as drivers/Pixis.py does, in sequence mode. """

    def __init__(self, args):
        super().__init__(args)
        from pylablib.devices import PrincetonInstruments
        print('Starting the Pixis camera ...')
        print('  cameras found:', PrincetonInstruments.list_cameras())
        self.cam = PrincetonInstruments.PicamCamera()
        cam = self.cam
        self.tick_hz = None
        self.has_timestamps = False
        self._period_locked = False

        width, height = cam.get_detector_size()
        y0 = int(np.clip(args.roi_y0, 0, height - 1))
        h = int(np.clip(args.roi_height or (height - y0), 1, height - y0))
        # same ROI definition as drivers/Pixis.py: rows summed on chip into a single row
        cam.set_attribute_value('ROIs', [{'x': 0, 'width': width, 'x_binning': 1,
                                          'y': y0, 'height': h, 'y_binning': h}])
        cam.set_exposure(args.exposure_ms * 1e-3)
        if args.shutter == 'open':
            # the mechanical shutter would otherwise open and close around every short frame
            self._set_attr(('Shutter Timing Mode',), 'AlwaysOpen')
        if args.adc_speed_mhz:
            self._set_attr(('ADC Speed', 'Adc Speed'), float(args.adc_speed_mhz))
        try:
            cam.enable_metadata(True)
            self.tick_hz = self._get_attr(('Time Stamp Resolution',))
            self.has_timestamps = bool(self.tick_hz)
        except Exception as error:
            print('  frame time stamps unavailable (%s): the nominal frame period is used' % error)

        exposure, period = cam.get_frame_timings()
        print('  ROI rows %d-%d binned into one row, exposure %.2f ms, nominal frame period %.2f ms'
              % (y0, y0 + h - 1, exposure * 1e3, period * 1e3))
        for label, names in (('ADC speed', ('ADC Speed', 'Adc Speed')), ('ADC quality', ('ADC Quality', 'Adc Quality')),
                             ('shutter timing', ('Shutter Timing Mode',)),
                             ('readout time (ms)', ('Readout Time Calculation',)),
                             ('clean cycles', ('Clean Cycle Count',))):
            print('  %-18s %s' % (label, self._get_attr(names)))
        self.scan_us = period * 1e6
        self.nos = nos_for_window(args, self.scan_us)
        # ring buffer larger than the acquisition, so that frames are still there when they are read
        cam.setup_acquisition(mode='sequence', nframes=2 * self.nos + 16)

    def _find_attr(self, *names):
        """ Attribute name as spelled by pylablib for the first candidate that exists (case/space insensitive). """
        try:
            attributes = self.cam.get_all_attributes()
            keys = list(attributes.keys()) if hasattr(attributes, 'keys') else list(attributes)
        except Exception:
            return None
        norm = lambda text: ''.join(ch for ch in str(text).lower() if ch.isalnum())
        table = {norm(key): key for key in keys}
        for name in names:
            if norm(name) in table:
                return table[norm(name)]
        return None

    def _get_attr(self, names):
        name = self._find_attr(*names)
        if name is None:
            return None
        try:
            return self.cam.get_attribute_value(name)
        except Exception as error:
            return 'unreadable (%s)' % error

    def _set_attr(self, names, value):
        name = self._find_attr(*names)
        if name is None:
            print('  attribute not found (%s): left unchanged' % names[0])
            return False
        try:
            self.cam.set_attribute_value(name, value)
            return True
        except Exception as error:
            print('  could not set %s to %s: %s' % (name, value, error))
            return False

    def acquire(self):
        """ One blocking acquisition returning ALL frames, as (nos, npix) counts (sum of the binned rows). """
        cam, n = self.cam, self.nos
        t0 = time.perf_counter()
        cam.start_acquisition()
        try:
            budget = 10.0 + 3 * n * self.scan_us * 1e-6
            cam.wait_for_frame(since='start', nframes=n, timeout=budget)
            frames, infos = cam.read_multiple_images(rng=(0, n), return_info=True)
        finally:
            cam.stop_acquisition()
        self.last_call_s = time.perf_counter() - t0
        if frames is None or len(frames) < n:
            raise RuntimeError('Pixis delivered %d frames out of %d' % (0 if frames is None else len(frames), n))
        scans = np.array([np.asarray(f, dtype=np.float32).reshape(-1, f.shape[-1]).sum(axis=0) for f in frames[:n]],
                         dtype=np.float32)
        self._update_period(infos)
        return scans

    def _update_period(self, infos):
        """ Takes the frame period from the camera time stamps (first acquisition only) and checks its regularity. """
        if self._period_locked or not self.has_timestamps or not infos or any(i is None for i in infos):
            return
        starts = np.array([i.timestamp_start for i in infos], dtype=float) / float(self.tick_hz)
        steps = np.diff(starts)
        measured_us = float(np.median(steps) * 1e6)
        print('  frame period from time stamps: %.2f ms (nominal %.2f ms), step jitter %.3f ms'
              % (measured_us / 1e3, self.scan_us / 1e3, (steps.max() - steps.min()) * 1e3))
        if measured_us > 0:
            self.scan_us = measured_us
        self._period_locked = True

    def close_camera(self):
        self.cam.stop_acquisition()
        self.cam.close()


class SimRig:
    """ Fake SLM + camera obeying a simple model (latency + frame quantisation + exponential settling), to test the
        analysis chain without hardware. Phase-only changes produce a short intensity transient. """
    width, height = 480, 300
    npix = 1010

    def __init__(self, args, latency_s=0.045, frame_s=1 / 60, tau_s=0.025, start_lag_s=0.004):
        self.stresing_like = args.camera == 'stresing'
        self.scan_us = float(args.stimer_us if self.stresing_like else 4000)
        self.nos = nos_for_window(args, self.scan_us)
        self.first_valid = args.first_valid
        self.latency_s, self.frame_s, self.tau_s, self.start_lag_s = latency_s, frame_s, tau_s, start_lag_s
        self.rng = np.random.default_rng(args.seed)
        self.events, self.last_call_s = [], 0.0
        self._log, self._level, self._image = [], 0.0, None
        pix = np.arange(self.npix)
        self._band = np.exp(-0.5 * ((pix - 500) / 80) ** 2)

    def write(self, image):
        onset = time.perf_counter() + self.latency_s + self.rng.uniform(0, self.frame_s)
        level = float((image.max(axis=1) > 0).mean())
        changed = self._image is None or not np.array_equal(image, self._image)
        phase_only = changed and self._image is not None and abs(level - self._level) < 1e-9
        self._log.append(dict(t=onset, prev=self._level, level=level, phase_only=phase_only))
        self._level, self._image = level, image.copy()

    def sleep(self, seconds):
        time.sleep(seconds)

    def _state(self, t):
        level, dip = (self._log[0]['prev'] if self._log else 0.0), 0.0
        for event in sorted(self._log, key=lambda e: e['t']):
            if event['t'] > t:
                break
            x = (t - event['t']) / self.tau_s
            level = event['prev'] + (event['level'] - event['prev']) * (1 - np.exp(-x))
            dip = 0.5 * x * np.exp(1 - x) if event['phase_only'] else 0.0
        return level, dip

    def acquire(self):
        t0 = time.perf_counter()
        dt = self.scan_us * 1e-6
        time.sleep(self.start_lag_s + self.nos * dt)
        scans = np.empty((self.nos, self.npix), np.float32)
        for k in range(self.nos):
            level, dip = self._state(t0 + self.start_lag_s + k * dt)
            signal = 200 + (0.1 + 0.9 * level) * 20000 * self._band * (1 - dip)
            scans[k] = signal + self.rng.normal(0, 30, self.npix)
        if self.stresing_like:
            scans[:4] += 3000 * self.rng.random((4, 1))   # crosstalk of the first scans, discarded by the driver
        self.last_call_s = time.perf_counter() - t0
        return scans

    def close(self):
        pass


# ----------------------------------------------------------------------------------------------------------------------
# Experiments
# ----------------------------------------------------------------------------------------------------------------------
def calibrate_mask(rig, image_off, image_on, args):
    """ Finds the pixels that carry the diffracted light, and checks that there is enough of it. """
    print('Contrast check (pattern off / on) ...')
    rig.write(image_off)
    rig.sleep(args.rest_s)
    s_off = steady_state(rig.acquire(), rig.first_valid)
    rig.write(image_on)
    rig.sleep(args.rest_s)
    scans_on = rig.acquire()
    s_on = steady_state(scans_on, rig.first_valid)
    diff = s_on - s_off
    mask = np.abs(diff) > 0.2 * np.abs(diff).max()
    noise = float(np.median(scans_on[rig.first_valid:, mask].std(axis=0)))
    snr = float(np.abs(diff)[mask].mean() / max(noise, 1e-12))
    print('  %d signal pixels, mean |on-off| / noise per scan = %.1f, max count = %.0f'
          % (mask.sum(), snr, scans_on.max()))
    if scans_on.max() >= SATURATION:
        raise SystemExit('The camera is saturated: attenuate the beam or shorten the exposure, then run again.')
    if mask.sum() < 3 or snr < 5:
        raise SystemExit('Not enough diffracted light on the camera (pattern on vs off): align the beam, or '
                         'increase the exposure (Pixis).')
    return mask


def trial_real(rig, before, after, delta_ms, args):
    rig.write(before)
    rig.sleep(args.rest_s)
    rig.events.clear()
    t_write = time.perf_counter()
    rig.write(after)
    rig.sleep(delta_ms / 1000.0)
    t_call = time.perf_counter()
    scans = rig.acquire()
    return scans, dict(t_write=t_write, t_call=t_call, call_s=rig.last_call_s, events=list(rig.events))


def trial_prestart(rig, before, after, delay_ms, args):
    rig.write(before)
    rig.sleep(args.rest_s)
    rig.events.clear()
    box = {}

    def acquisition():
        box['t_call'] = time.perf_counter()
        box['scans'] = rig.acquire()

    thread = threading.Thread(target=acquisition)
    thread.start()
    rig.sleep(delay_ms / 1000.0)
    t_write = time.perf_counter()
    rig.write(after)
    while thread.is_alive():
        rig.sleep(0.005)
    thread.join()
    if 'scans' not in box:
        raise RuntimeError('The acquisition thread failed (see the messages above).')
    return box['scans'], dict(t_write=t_write, t_call=box['t_call'], call_s=rig.last_call_s, events=list(rig.events))


def trace_offsets_ms(events):
    """ Time of every stage of the SLM write chain, in ms after the 'call' stamp (first occurrence). """
    if not events or events[0][0] != 'call':
        return {}
    t0, out = events[0][1], {}
    for name, t in events:
        out.setdefault(name, (t - t0) * 1e3)
    return out


def run_real_sweep(rig, name, images, mask, args, rng):
    image_a, image_b = images
    scan_ms = rig.scan_us / 1e3
    refs = []
    for image in (image_a, image_b):
        rig.write(image)
        rig.sleep(args.rest_s)
        refs.append(steady_state(rig.acquire(), rig.first_valid))
    trials = []
    total = args.repeats * len(args.deltas)
    for rep in range(args.repeats):
        order = list(args.deltas)
        rng.shuffle(order)
        direction = rep % 2                          # 0: a -> b, 1: b -> a
        before, after = ((image_a, image_b), (image_b, image_a))[direction]
        for delta in order:
            scans, info = trial_real(rig, before, after, delta, args)
            res = analyze_real(scans, refs[direction], mask, rig.first_valid)
            res['app_err'] = app_window_error(scans, res, mask, scan_ms, args.app_start_ms, args.app_end_ms)
            trials.append(dict(delta=delta, direction=direction, scans_binned=bin_pixels(scans, args.bin).astype(np.float32),
                               res=res, info=info))
            print('  [%s] %3d/%d  delta=%3d ms dir=%d  settle=%.1f ms stale=%d'
                  % (name, len(trials), total, delta, direction, res['settle_idx'] * scan_ms, res['stale']))
    return trials


def run_prestart(rig, name, images, mask, args):
    image_a, image_b = images
    scan_ms = rig.scan_us / 1e3
    trials = []
    for rep in range(args.prestart_repeats):
        before, after = ((image_a, image_b), (image_b, image_a))[rep % 2]
        scans, info = trial_prestart(rig, before, after, args.prestart_delay_ms, args)
        res = analyze_prestart(scans, args.prestart_delay_ms, rig.scan_us, mask, rig.first_valid)
        write_ms = (info['t_write'] - info['t_call']) * 1e3
        res['write_ms'] = write_ms
        res['onset_ms'] = None if res['onset_idx'] is None else res['onset_idx'] * scan_ms
        res['l_minus_c_ms'] = None if res['onset_ms'] is None else res['onset_ms'] - write_ms
        res['duration_ms'] = None if res['duration_scans'] is None else res['duration_scans'] * scan_ms
        trials.append(dict(direction=rep % 2, scans_binned=bin_pixels(scans, args.bin).astype(np.float32),
                           res=res, info=info))
        print('  [%s] prestart %d/%d  write at %.1f ms  onset=%s  duration=%s'
              % (name, rep + 1, args.prestart_repeats, write_ms,
                 'none' if res['onset_ms'] is None else '%.1f ms' % res['onset_ms'],
                 'none' if res['duration_ms'] is None else '%.1f ms' % res['duration_ms']))
    return trials


# ----------------------------------------------------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------------------------------------------------
def summarize(name, real, prestart, rig, args):
    scan_ms = rig.scan_us / 1e3
    lines = ['', '=== transition %s ===' % name,
             'delta_ms |  n | stale trials | settle after camera start, ms: median / p95 / max | '
             'application-window error: median / max | contrast / single-scan noise (median)']
    deltas = sorted(set(t['delta'] for t in real))
    low_contrast = np.median([t['res']['contrast_snr'] for t in real]) < 3
    for delta in deltas:
        sel = [t for t in real if t['delta'] == delta]
        settle = np.array([t['res']['settle_idx'] for t in sel]) * scan_ms
        stale = np.array([t['res']['stale'] for t in sel])
        errors = [t['res']['app_err'] for t in sel if t['res']['app_err'] is not None]
        err_text = 'n/a' if (low_contrast or not errors) else '%.3f / %.3f' % (np.median(errors), np.max(errors))
        snr = np.median([t['res']['contrast_snr'] for t in sel])
        lines.append('%8d | %2d | %5.0f %%       | %7.1f / %7.1f / %7.1f                          | %-23s | %8.1f'
                     % (delta, len(sel), 100.0 * np.mean(stale > 0), np.median(settle),
                        np.percentile(settle, 95), settle.max(), err_text, snr))
    clean = [d for d in deltas if all(t['res']['stale'] == 0 for t in real if t['delta'] == d)]
    lines.append('time resolution: one scan every %.2f ms' % scan_ms)
    lines.append('smallest delta with no stale scan (first %d scans ignored): %s'
                 % (rig.first_valid, '%d ms' % clean[0] if clean else 'none in the tested range, test larger deltas'))
    if low_contrast:
        lines.append('application-window error not evaluated: intensity contrast too low for this transition.')
    else:
        ok_app = [d for d in deltas
                  if all(t['res']['app_err'] is not None and t['res']['app_err'] <= args.app_tolerance
                         for t in real if t['delta'] == d)]
        lines.append('application-like measurement (average of the scans in %.0f-%.0f ms after the camera start, '
                     'tolerance %.1f %%): pause needed before the camera call >= %s'
                     % (args.app_start_ms, args.app_end_ms, 100 * args.app_tolerance,
                        '%d ms (measured grid)' % ok_app[0] if ok_app else 'more than the largest tested delta'))
    if any(not t['res']['tail_ok'] for t in real):
        lines.append('WARNING: the end of some acquisitions was still drifting: increase --window-ms.')
    if low_contrast:
        lines.append('WARNING: low intensity contrast for this transition (phase-only change?). Stale scans are only '
                     'detected through an intensity transient: the absence of stale scans does NOT prove that the '
                     'phase is settled. An interferometric check (two overlapping beams) is needed.')
    for direction in (0, 1):
        sel = [t for t in real if t['delta'] == deltas[0] and t['direction'] == direction]
        if sel:
            lines.append('  direction %s, delta=%d ms: settle median %.1f ms (n=%d)'
                         % ('a->b' if direction == 0 else 'b->a', deltas[0],
                            np.median([t['res']['settle_idx'] for t in sel]) * scan_ms, len(sel)))
    overhead = np.median([t['info']['call_s'] for t in real]) - rig.nos * scan_ms / 1e3
    lines.append('blocking camera call lasts %.1f ms more than nos x scan period (start overhead, cleaning, block timer)'
                 % (overhead * 1e3))
    traces = [trace_offsets_ms(t['info']['events']) for t in real]
    traces = [tr for tr in traces if tr]
    if traces:
        lines.append('SLM write chain, ms after Slm.write_image() call (median / max over %d writes):' % len(traces))
        for stage in ('queued', 'worker_pickup', 'driver_in', 'driver_out', 'worker_done', 'flag_main_thread'):
            values = [tr[stage] for tr in traces if stage in tr]
            if values:
                lines.append('    %-17s %7.1f / %7.1f' % (stage, np.median(values), np.max(values)))
    if prestart:
        found = [t['res'] for t in prestart if t['res']['onset_ms'] is not None]
        lines.append('prestart (camera started first): onset detected in %d/%d trials' % (len(found), len(prestart)))
        if found:
            lcs = np.array([r['l_minus_c_ms'] for r in found])
            dur = np.array([r['duration_ms'] for r in found])
            lines.append('    transition duration (onset -> settled): median %.1f ms, max %.1f ms' % (np.median(dur), dur.max()))
            lines.append('    L - c (SLM latency minus delay between camera call and first scan): '
                         'median %.1f ms, min %.1f, max %.1f (spread %.1f ms; one 60 Hz frame = 16.7 ms)'
                         % (np.median(lcs), lcs.min(), lcs.max(), lcs.max() - lcs.min()))
        else:
            lines.append('    no transient detected: this transition is probably invisible in intensity (phase only).')
    return lines


def save_results(out, args, rig, mask, results):
    import h5py
    with h5py.File(out / 'results.h5', 'w') as f:
        f.attrs.update(dict(camera=args.camera, scan_us=rig.scan_us, nos=rig.nos, first_valid=rig.first_valid,
                            deltas_ms=list(args.deltas), rest_s=args.rest_s, simulate=args.simulate,
                            exposure_ms=args.exposure_ms, app_start_ms=args.app_start_ms, app_end_ms=args.app_end_ms,
                            created=datetime.datetime.now().isoformat()))
        f['mask'] = mask
        for name, (real, prestart) in results.items():
            for label, trials in (('real', real), ('prestart', prestart)):
                if not trials:
                    continue
                g = f.create_group('%s/%s' % (label, name))
                g['scans_binned'] = np.stack([t['scans_binned'] for t in trials])
                g['d'] = np.stack([t['res']['d'] for t in trials]).astype(np.float32)
                g['settle_idx'] = [t['res']['settle_idx'] for t in trials]
                g['direction'] = [t['direction'] for t in trials]
                if label == 'real':
                    g['delta_ms'] = [t['delta'] for t in trials]
                    g['app_err'] = [np.nan if t['res']['app_err'] is None else t['res']['app_err'] for t in trials]
                else:
                    g['onset_idx'] = [-1 if t['res']['onset_idx'] is None else t['res']['onset_idx'] for t in trials]
                    g['write_ms'] = [t['res']['write_ms'] for t in trials]


def plot_results(out, name, real, rig, args):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib not available: no figure.')
        return
    scan_ms = rig.scan_us / 1e3
    deltas = sorted(set(t['delta'] for t in real))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for delta in deltas:
        curves = np.array([t['res']['d'] / max(t['res']['d_ref'], 1e-12) for t in real if t['delta'] == delta])
        ax1.plot(np.arange(curves.shape[1]) * scan_ms, np.median(curves, axis=0), label='delta=%d ms' % delta)
    ax1.axvspan(args.app_start_ms, args.app_end_ms, color='gray', alpha=0.15, label='application window')
    ax1.set_xlabel('time after camera start (ms)')
    ax1.set_ylabel('distance to final spectrum / |after - before|')
    ax1.set_yscale('log')
    ax1.legend(fontsize=7)
    ax2.scatter([t['delta'] for t in real], [t['res']['settle_idx'] * scan_ms for t in real], s=8)
    ax2.axhline(args.app_start_ms, color='r', ls='--', label='start of the application window')
    ax2.set_xlabel('pause between write_image and camera call (ms)')
    ax2.set_ylabel('settle time after camera start (ms)')
    ax2.legend(fontsize=7)
    fig.suptitle('SLM settling (%s), transition %s' % (args.camera, name))
    fig.tight_layout()
    fig.savefig(out / ('settling_%s.png' % name), dpi=120)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--camera', choices=('pixis', 'stresing'), default='pixis')
    p.add_argument('--simulate', action='store_true', help='fake SLM and camera, to test the analysis chain')
    p.add_argument('--transitions', nargs='+', choices=TRANSITIONS, default=['onoff', 'cep_pi', 'rows10'])
    p.add_argument('--deltas', nargs='+', type=int, default=[0, 20, 40, 60, 80, 120, 200, 300],
                   help='pauses (ms) between write_image and the camera call in the real-flow sweep')
    p.add_argument('--repeats', type=int, default=12, help='trials per delta (use an even number: both directions)')
    p.add_argument('--prestart-repeats', type=int, default=8)
    p.add_argument('--prestart-delay-ms', type=int, default=100)
    p.add_argument('--window-ms', type=float, default=500.0,
                   help='duration of one acquisition; it must cover latency + settling + a settled tail')
    p.add_argument('--nos', type=int, default=None, help='number of scans (default: window-ms / frame period)')
    p.add_argument('--first-valid', type=int, default=None,
                   help='leading scans ignored (default: 4 for the Stresing driver, 0 for the Pixis)')
    # Pixis
    p.add_argument('--exposure-ms', type=float, default=2.0, help='Pixis exposure per frame (raise it if the signal is weak)')
    p.add_argument('--roi-y0', type=int, default=0, help='Pixis first row of the signal band')
    p.add_argument('--roi-height', type=int, default=None, help='Pixis number of rows binned (default: up to the last row)')
    p.add_argument('--shutter', choices=('open', 'keep'), default='open',
                   help="Pixis shutter: 'open' holds it open during the test (conservative), 'keep' leaves the setting")
    p.add_argument('--adc-speed-mhz', type=float, default=None, help='Pixis ADC speed (e.g. 2 or 0.1); default: unchanged')
    # Stresing
    p.add_argument('--stimer-us', type=int, default=1000, help='Stresing scan interval during the test')
    p.add_argument('--block-interval-us', type=int, default=None,
                   help='Stresing block timer; None keeps the value of the camera config, as the application does')
    # what the application measurement looks like, to translate the result
    p.add_argument('--app-exposure-ms', type=float, default=100.0, help='Pixis application exposure (int_time)')
    p.add_argument('--app-discard', type=int, default=4, help='Stresing scans discarded by the driver')
    p.add_argument('--app-stimer-us', type=int, default=10000, help='Stresing scan interval of the application config')
    p.add_argument('--app-nos', type=int, default=10, help='Stresing scans per application acquisition')
    p.add_argument('--app-start-ms', type=float, default=None)
    p.add_argument('--app-end-ms', type=float, default=None)
    p.add_argument('--app-tolerance', type=float, default=0.02,
                   help='accepted relative error of an application-like measurement')
    p.add_argument('--rest-s', type=float, default=1.5, help='rest before each change so the liquid crystal relaxes')
    p.add_argument('--grating-period', type=int, default=50)
    p.add_argument('--bin', type=int, default=16, help='pixel binning of the saved scans')
    p.add_argument('--out', default='C:/data/Colbert/slm_settling')
    p.add_argument('--no-trace', action='store_true', help='do not time-stamp the SLM write chain')
    p.add_argument('--plot', action='store_true')
    p.add_argument('--seed', type=int, default=0)
    args = p.parse_args(argv)
    stresing = args.camera == 'stresing'
    if args.first_valid is None:
        args.first_valid = 4 if stresing else 0
    if args.app_start_ms is None:
        args.app_start_ms = args.app_discard * args.app_stimer_us / 1e3 if stresing else 0.0
    if args.app_end_ms is None:
        args.app_end_ms = args.app_nos * args.app_stimer_us / 1e3 if stresing else args.app_exposure_ms
    return args


def main(argv=None):
    args = parse_args(argv)
    out = Path(args.out) / datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    if args.simulate:
        rig = SimRig(args)
    else:
        rig = PixisRig(args) if args.camera == 'pixis' else StresingRig(args)
    results, report = {}, []
    try:
        if args.window_ms < args.app_end_ms + 100 and not args.nos:
            print('WARNING: --window-ms is short compared with the application window (%.0f ms).' % args.app_end_ms)
        print('Camera %s: %d scans of %.2f ms per acquisition (%.0f ms)'
              % (args.camera, rig.nos, rig.scan_us / 1e3, rig.nos * rig.scan_us / 1e3))
        all_images = build_images(rig.width, rig.height, args.grating_period)
        mask = calibrate_mask(rig, *all_images['onoff'], args)
        for name in args.transitions:
            print('Transition %s: real-flow sweep' % name)
            real = run_real_sweep(rig, name, all_images[name], mask, args, rng)
            print('Transition %s: prestart runs' % name)
            prestart = run_prestart(rig, name, all_images[name], mask, args) if args.prestart_repeats else []
            results[name] = (real, prestart)
            report += summarize(name, real, prestart, rig, args)
            if args.plot:
                plot_results(out, name, real, rig, args)
    finally:
        rig.close()
    text = '\n'.join(report)
    print(text)
    (out / 'summary.txt').write_text(text, encoding='utf-8')
    save_results(out, args, rig, mask, results)
    print('\nResults saved in', out)


if __name__ == '__main__':
    main()
