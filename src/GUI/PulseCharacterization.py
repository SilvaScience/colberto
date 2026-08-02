"""
TG-FROG acquisition tab: pick the probe beam (scanned in delay, conjugated in the signal) and
the two grating beams (held at their own current phase, zero relative delay), set the delay
scan range, and launch a TGFROGMeasurement. Shows the running (delay, wavelength) trace live.

Retrieval is intentionally not done here: the trace is exported through DataHandling like any
other calibration measurement, and retrieved offline with samples/retrieval/tgfrog_retrieval.py
(pypret). See src/measurements/TGFROGClasses.py for the acquisition physics/conventions.
"""

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np


class PulseCharacterization(QtWidgets.QWidget):
    """
        Controls and live display for a TG-FROG delay scan.
    """

    def __init__(self, parent=None):
        super(PulseCharacterization, self).__init__(parent)

        # ---- beam role selection ----
        self.probe_beam_box = QtWidgets.QComboBox()
        self.grating_beam1_box = QtWidgets.QComboBox()
        self.grating_beam2_box = QtWidgets.QComboBox()

        beam_box = QtWidgets.QGroupBox('Beam roles')
        beam_layout = QtWidgets.QFormLayout()
        beam_layout.addRow('Probe (scanned, conjugated):', self.probe_beam_box)
        beam_layout.addRow('Grating beam 1:', self.grating_beam1_box)
        beam_layout.addRow('Grating beam 2:', self.grating_beam2_box)
        beam_box.setLayout(beam_layout)

        # ---- scan parameters ----
        self.probe_wavelength_spin = QtWidgets.QDoubleSpinBox()
        self.probe_wavelength_spin.setRange(200, 1600)
        self.probe_wavelength_spin.setValue(800)
        self.probe_wavelength_spin.setSuffix(' nm')

        self.delay_min_spin = QtWidgets.QSpinBox()
        self.delay_min_spin.setRange(-100000, 100000)
        self.delay_min_spin.setValue(-200)
        self.delay_min_spin.setSuffix(' fs')

        self.delay_max_spin = QtWidgets.QSpinBox()
        self.delay_max_spin.setRange(-100000, 100000)
        self.delay_max_spin.setValue(200)
        self.delay_max_spin.setSuffix(' fs')

        self.delay_step_spin = QtWidgets.QSpinBox()
        self.delay_step_spin.setRange(1, 10000)
        self.delay_step_spin.setValue(2)
        self.delay_step_spin.setSuffix(' fs')

        self.demo_mode_checkbox = QtWidgets.QCheckBox('Demo mode (synthetic trace, no hardware)')

        scan_box = QtWidgets.QGroupBox('Delay scan')
        scan_layout = QtWidgets.QFormLayout()
        scan_layout.addRow('Probe carrier wavelength:', self.probe_wavelength_spin)
        scan_layout.addRow('Delay min:', self.delay_min_spin)
        scan_layout.addRow('Delay max:', self.delay_max_spin)
        scan_layout.addRow('Delay step:', self.delay_step_spin)
        scan_layout.addRow(self.demo_mode_checkbox)
        scan_box.setLayout(scan_layout)

        # ---- controls ----
        """ No local Stop button: the main window already has one global stop_pushButton wired
        to stop_measurement(), shared by every measurement type. A second one here would either
        duplicate it or drift out of sync with which QThread is actually running. """
        self.start_button = QtWidgets.QPushButton('Start TG-FROG scan')
        self.status_label = QtWidgets.QLabel('Idle.')
        self.export_hint_label = QtWidgets.QLabel(
            'When the scan finishes, use the "Save calibration" button (not the plain "Save" '
            'button, which does not handle nested calibration data) to export the trace, then '
            'run samples/retrieval/tgfrog_retrieval.py offline to reconstruct the pulse.')
        self.export_hint_label.setWordWrap(True)

        left_panel = QtWidgets.QVBoxLayout()
        left_panel.addWidget(beam_box)
        left_panel.addWidget(scan_box)
        left_panel.addWidget(self.start_button)
        left_panel.addWidget(self.status_label)
        left_panel.addWidget(self.export_hint_label)
        left_panel.addStretch(1)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(320)

        # ---- 2D trace plot ----
        """ Same (delay, wavelength) data convention and column-major ImageItem as
        DelayCalibrationPlot: data[delay_idx, wl_idx] plots directly with no transpose. """
        self.graphLayoutWidget = pg.GraphicsLayoutWidget()
        self.plot = self.graphLayoutWidget.addPlot()
        self.plot.setLabel('bottom', 'Delay [fs]')
        self.plot.setLabel('left', 'Wavelength [nm]')
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        self.histogram = pg.HistogramLUTItem()
        self.histogram.setImageItem(self.image)
        self.graphLayoutWidget.addItem(self.histogram)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(left_widget)
        layout.addWidget(self.graphLayoutWidget, stretch=1)
        self.setLayout(layout)

    @QtCore.pyqtSlot(object)
    def update_beam_names(self, beam_dict):
        """
            Refreshes the three beam dropdowns, keeping the current selection if it is still
            valid.
            input:
                - beam_dict: dict of beam name -> Beam, as emitted by DataHandling.sendBeams
        """
        for box in (self.probe_beam_box, self.grating_beam1_box, self.grating_beam2_box):
            current = box.currentText()
            box.clear()
            box.addItems(list(beam_dict))
            if current in beam_dict:
                box.setCurrentText(current)

    @QtCore.pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def set_data(self, delay_array, wavelength_array, data):
        """
            Updates the live 2D trace display.
            input:
                - delay_array: (np.ndarray) probe delay axis, fs
                - wavelength_array: (np.ndarray) spectrometer wavelength axis, nm
                - data: (np.ndarray) 2D array, shape (len(delay_array), len(wavelength_array))
        """
        if np.shape(data)[0] >= 2 and np.shape(data)[1] >= 2:
            deltax = delay_array[1] - delay_array[0]
            deltay = wavelength_array[1] - wavelength_array[0]
            rect = QtCore.QRectF(
                delay_array[0] - deltax / 2, wavelength_array[0] - deltay / 2,
                delay_array[-1] - delay_array[0], wavelength_array[-1] - wavelength_array[0])
            self.image.setImage(data, autoLevels=True)
            self.image.setRect(rect)
            self.histogram.setLevels(*self.image.getLevels())

    def set_running(self, running):
        """
            Updates button/status state when a scan starts or ends.
            input:
                - running: (bool)
        """
        self.start_button.setEnabled(not running)
        self.status_label.setText('Scanning...' if running else 'Idle.')
