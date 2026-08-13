"""
Standalone reproduction/verification for:
'Switching camera disconnects datahandler from Beamexplorer'

Exercises the exact signal-wiring pattern used in main.py's __init__ and
on_spectrometer_changed, without needing real hardware (DataHandling and
BeamExplorer are pure Python/Qt).

Usage:
    python _bugtest_camera_switch_beamexplorer.py old   # reproduces the bug (pre-fix wiring)
    python _bugtest_camera_switch_beamexplorer.py new   # verifies the fix (post-fix wiring)
"""
import sys
from PyQt5 import QtWidgets
from DataHandling.DataHandling import DataHandling
from GUI.BeamExplorer import BeamExplorer
from compute.beams import Beam


def make_beam():
    # Minimal Beam; only needs to be a distinct object stored in the dict.
    return Beam()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "new"
    app = QtWidgets.QApplication(sys.argv)

    parameter = {}
    spec_length = 100

    # --- Step 1: initial startup, mirrors main.py __init__ ---
    dh1 = DataHandling(parameter, spec_length)
    beam_explorer = BeamExplorer(dh1.get_beams())

    dh1.sendBeams.connect(beam_explorer.receive_beams)
    beam_explorer.beams_changed.connect(dh1.set_multiple_beams)

    # --- Step 2: switch camera/detector, mirrors on_spectrometer_changed ---
    dh1.close()
    dh2 = DataHandling(parameter, spec_length)

    if mode == "new":
        # the fix: re-wire beam signals to the new DataHandling instance
        dh2.sendBeams.connect(beam_explorer.receive_beams)
        beam_explorer.beams_changed.connect(dh2.set_multiple_beams)
    # mode == "old": deliberately omit the reconnect, reproducing the bug

    # --- Step 3: "Assign beams" button press equivalent ---
    dh2.set_beam(("beam1", make_beam()))

    got_it = "beam1" in beam_explorer.beamDict
    print(f"mode={mode}: beam_explorer received update = {got_it}")
    assert got_it == (mode == "new"), "Unexpected result for this mode"
    print("OK" if got_it == (mode == "new") else "FAIL")


if __name__ == "__main__":
    main()
