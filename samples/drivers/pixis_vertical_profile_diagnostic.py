# -*- coding: utf-8 -*-
"""
Standalone diagnostic for the PIXIS vertical readout.

The PIXIS is a 2D sensor (1024 columns x ~256 rows). On a spectrograph the horizontal axis is
wavelength and the vertical axis is position along the entrance slit, so the signal only occupies
the rows where the beam is imaged. Reading a single row samples one height in the slit and throws
away everything else.

This script reads one full frame, shows where the signal actually sits vertically, and reports how
much signal a single-row readout would miss. Use the y0/height it suggests with
Pixis.set_binned_roi(y0, height).

Runs on its own, outside the COLBERTo interface, and changes nothing in the repository.
Requires pylablib and a connected camera. Matplotlib is optional (text output works without it).

    python samples/drivers/pixis_vertical_profile_diagnostic.py
    python samples/drivers/pixis_vertical_profile_diagnostic.py --exposure 200 --frames 5
"""

import argparse
import sys
import time

import numpy as np


def acquire_full_frame(exposure_ms, n_frames):
    """
        Connects to the PIXIS, forces a full-frame unbinned readout and averages a few frames.
        input:
            - exposure_ms (float): exposure time in ms
            - n_frames (int): number of frames to average
        output:
            - np.ndarray: 2D frame (rows x columns), averaged over n_frames
    """
    from pylablib.devices import PrincetonInstruments

    print('Cameras found:', PrincetonInstruments.list_cameras())
    camera = PrincetonInstruments.PicamCamera()
    print('Camera connected')

    try:
        width, height = camera.get_detector_size()
    except Exception as e:
        width, height = 1024, 256
        print(f'Could not query detector size, assuming {width}x{height}. {e}')
    print(f'Sensor: {width} columns x {height} rows')

    # Full frame, no binning: every row read separately.
    roi = {"x": 0, "width": width, "x_binning": 1, "y": 0, "height": height, "y_binning": 1}
    camera.set_attribute_value("ROIs", [roi])
    camera.set_attribute_value("Exposure Time", int(exposure_ms))

    camera.start_acquisition()
    frames = []
    try:
        for i in range(n_frames):
            frame = None
            deadline = time.time() + exposure_ms / 1e3 + 5.0
            while frame is None and time.time() < deadline:
                time.sleep(0.02)
                frame = camera.read_newest_image()
            if frame is None:
                print(f'  frame {i + 1}/{n_frames}: timeout, skipped')
                continue
            frames.append(np.asarray(frame, dtype=float))
            print(f'  frame {i + 1}/{n_frames}: shape {np.shape(frame)}')
    finally:
        camera.stop_acquisition()
        try:
            camera.close()
        except Exception:
            pass

    if not frames:
        raise RuntimeError('No frame acquired. Check exposure time and that light reaches the camera.')
    return np.mean(frames, axis=0)


def analyse(frame, floor_fraction=0.1):
    """
        Locates the signal band along the vertical axis and quantifies what a single-row readout loses.
        input:
            - frame (np.ndarray): 2D frame (rows x columns)
            - floor_fraction (float): fraction of the peak above baseline used to delimit the band
        output:
            - dict: analysis results, including the suggested y0 and height
    """
    frame = np.asarray(frame, dtype=float)
    if frame.ndim != 2:
        raise ValueError(f'Expected a 2D frame, got shape {frame.shape}. '
                         'The ROI was probably not applied.')

    n_rows = frame.shape[0]
    profile = frame.sum(axis=1)                      # total counts per sensor row

    baseline = np.median(profile)
    contrast = profile - baseline
    peak_row = int(np.argmax(contrast))
    peak_value = contrast[peak_row]

    if peak_value <= 0:
        return dict(n_rows=n_rows, profile=profile, baseline=baseline, peak_row=peak_row,
                    signal_rows=np.array([], dtype=int), y0=0, height=n_rows,
                    flat=True, total=float(profile.sum()), row0=float(profile[0]),
                    band=float('nan'), gain_vs_row0=float('nan'))

    # Rows carrying a meaningful share of the peak define the band worth binning.
    signal_rows = np.where(contrast >= floor_fraction * peak_value)[0]
    y0, y1 = int(signal_rows.min()), int(signal_rows.max())
    height = y1 - y0 + 1

    band = float(profile[y0:y1 + 1].sum())
    row0 = float(profile[0])
    total = float(profile.sum())

    return dict(n_rows=n_rows, profile=profile, baseline=float(baseline), peak_row=peak_row,
                signal_rows=signal_rows, y0=y0, height=height, flat=False,
                total=total, row0=row0, band=band,
                gain_vs_row0=(band / row0 if row0 > 0 else float('inf')))


def report(res):
    """
        Prints the verdict in plain terms.
        input:
            - res (dict): output of analyse()
    """
    print('\n' + '=' * 64)
    print('VERTICAL PROFILE')
    print('=' * 64)
    print(f'Sensor rows read      : {res["n_rows"]}')

    if res['flat']:
        print('\nNo vertical structure found: the profile is flat.')
        print('Either no light is reaching the camera, or the ROI was not applied.')
        print('Check the shape printed above: a single row means the camera cropped the readout.')
        return

    print(f'Baseline (median row) : {res["baseline"]:.1f} counts')
    print(f'Brightest row         : {res["peak_row"]}')
    print(f'Signal band           : rows {res["y0"]} to {res["y0"] + res["height"] - 1} '
          f'({res["height"]} rows)')
    print()
    print(f'Counts in row 0 alone : {res["row0"]:.4g}   <- what the interface reads today')
    print(f'Counts in signal band : {res["band"]:.4g}')
    print(f'Counts in whole frame : {res["total"]:.4g}')
    print()

    gain = res['gain_vs_row0']
    if np.isfinite(gain):
        print(f'Binning the band collects {gain:.1f}x more signal than row 0 alone.')
    else:
        print('Row 0 collects essentially nothing: the signal is elsewhere on the sensor.')

    if res['peak_row'] > 5:
        print(f'\nThe signal is centred on row {res["peak_row"]}, not row 0, so a single-row readout')
        print('at y=0 is reading off the beam entirely.')

    print('\nSuggested measurement setting:')
    print(f'    spectrometer.set_binned_roi(y0={res["y0"]}, height={res["height"]})')
    print('\nOn chip binning also sums the charge before the readout amplifier, so the read noise is')
    print('paid once rather than once per row. The signal-to-noise gain is larger than the count')
    print('ratio above whenever the measurement is read-noise limited.')


def plot(frame, res):
    """
        Optional visual check: the frame and its vertical profile.
        input:
            - frame (np.ndarray): 2D frame
            - res (dict): output of analyse()
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('\n(matplotlib not available, skipping the plot)')
        return

    fig, (ax_img, ax_prof) = plt.subplots(1, 2, figsize=(12, 4.5),
                                          gridspec_kw={'width_ratios': [2, 1]})
    ax_img.imshow(frame, aspect='auto', origin='lower', interpolation='nearest')
    ax_img.set_xlabel('Column (wavelength)')
    ax_img.set_ylabel('Row (position along slit)')
    ax_img.set_title('Full frame')

    ax_prof.plot(res['profile'], np.arange(res['n_rows']))
    if not res['flat']:
        ax_prof.axhspan(res['y0'], res['y0'] + res['height'] - 1, alpha=0.25,
                        label=f'band: y0={res["y0"]}, h={res["height"]}')
        ax_prof.axhline(0, linestyle='--', linewidth=1, label='row 0 (read today)')
        ax_prof.legend(loc='best', fontsize=8)
    ax_prof.set_xlabel('Counts summed over wavelength')
    ax_prof.set_title('Vertical profile')

    fig.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--exposure', type=float, default=100.0, help='exposure time in ms')
    parser.add_argument('--frames', type=int, default=3, help='frames to average')
    parser.add_argument('--floor', type=float, default=0.1,
                        help='fraction of peak above baseline delimiting the signal band')
    parser.add_argument('--no-plot', action='store_true', help='text output only')
    parser.add_argument('--save', type=str, default=None, help='save the frame to this .npy file')
    args = parser.parse_args()

    try:
        frame = acquire_full_frame(args.exposure, args.frames)
    except Exception as e:
        print(f'\nAcquisition failed: {e}')
        return 1

    if args.save:
        np.save(args.save, frame)
        print(f'Frame saved to {args.save}')

    res = analyse(frame, floor_fraction=args.floor)
    report(res)
    if not args.no_plot:
        plot(frame, res)
    return 0


if __name__ == '__main__':
    sys.exit(main())
