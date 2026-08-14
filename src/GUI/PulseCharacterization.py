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


def _labeled_field(label_text, widget):
    """ Stacks a label above a field instead of QFormLayout's default of beside it. In a narrow
    column, a long label and a spinbox competing for one line left the spinbox with almost no
    width to show its own value -- stacking gives each its own full-width line instead. """
    container = QtWidgets.QVBoxLayout()
    container.setSpacing(1)
    container.addWidget(QtWidgets.QLabel(label_text))
    container.addWidget(widget)
    return container


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

        self.probe_beam_box.setToolTip('Scanned in delay; appears conjugated in the TG signal.')

        beam_box = QtWidgets.QGroupBox('Beam roles')
        beam_layout = QtWidgets.QFormLayout()
        beam_layout.addRow('Probe beam:', self.probe_beam_box)
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
        scan_layout = QtWidgets.QVBoxLayout()
        scan_layout.addLayout(_labeled_field('Probe carrier wavelength:', self.probe_wavelength_spin))
        scan_layout.addLayout(_labeled_field('Delay min:', self.delay_min_spin))
        scan_layout.addLayout(_labeled_field('Delay max:', self.delay_max_spin))
        scan_layout.addLayout(_labeled_field('Delay step:', self.delay_step_spin))
        scan_layout.addWidget(self.demo_mode_checkbox)
        scan_box.setLayout(scan_layout)

        # ---- simulator (demo mode) parameters ----
        """ Feeds TGFROGMeasurement's demo_* constructor arguments (see TGFROGClasses.py),
        which were previously only reachable by editing code. Only meaningful when demo mode is
        checked, since real acquisitions get their trace from the spectrometer, not these. """
        self.sim_fwhm_spin = QtWidgets.QDoubleSpinBox()
        self.sim_fwhm_spin.setRange(1, 500)
        self.sim_fwhm_spin.setValue(12)
        self.sim_fwhm_spin.setSuffix(' fs')

        self.sim_window_hint_label = QtWidgets.QLabel()
        self.sim_window_hint_label.setWordWrap(True)

        self.sim_gdd_spin = QtWidgets.QDoubleSpinBox()
        self.sim_gdd_spin.setRange(-100000, 100000)
        self.sim_gdd_spin.setValue(50)
        self.sim_gdd_spin.setSuffix(' fs^2')

        self.sim_tod_spin = QtWidgets.QDoubleSpinBox()
        self.sim_tod_spin.setRange(-1000000, 1000000)
        self.sim_tod_spin.setValue(100)
        self.sim_tod_spin.setSuffix(' fs^3')

        self.sim_noise_spin = QtWidgets.QDoubleSpinBox()
        self.sim_noise_spin.setRange(0, 100)
        self.sim_noise_spin.setValue(0)
        self.sim_noise_spin.setSuffix(' %')

        self.sim_window_spin = QtWidgets.QDoubleSpinBox()
        self.sim_window_spin.setRange(10, 2000)
        self.sim_window_spin.setValue(600)
        self.sim_window_spin.setSuffix(' nm')
        self.sim_window_spin.setToolTip(
            'Wavelength window kept in the synthetic trace, mimicking a spectrometer window. '
            'Narrow it towards a real grating\'s ~50 nm to see the accuracy loss from '
            'insufficient spectral coverage discussed for the current OPA / future NOPA.')

        self.simulator_box = QtWidgets.QGroupBox('Simulator (demo mode) parameters')
        simulator_layout = QtWidgets.QVBoxLayout()
        simulator_layout.addLayout(_labeled_field('Pulse FWHM:', self.sim_fwhm_spin))
        simulator_layout.addWidget(self.sim_window_hint_label)
        simulator_layout.addLayout(_labeled_field('GDD:', self.sim_gdd_spin))
        simulator_layout.addLayout(_labeled_field('TOD:', self.sim_tod_spin))
        simulator_layout.addLayout(_labeled_field('Noise level:', self.sim_noise_spin))
        simulator_layout.addLayout(_labeled_field('Spectral window:', self.sim_window_spin))
        self.simulator_box.setLayout(simulator_layout)
        self.simulator_box.setEnabled(False)

        # ---- controls ----
        """ No local Stop button: the main window already has one global stop_pushButton wired
        to stop_measurement(), shared by every measurement type. A second one here would either
        duplicate it or drift out of sync with which QThread is actually running. """
        self.start_button = QtWidgets.QPushButton('Start TG-FROG scan')
        self.status_label = QtWidgets.QLabel('Idle.')
        self.export_hint_label = QtWidgets.QLabel(
            'To save this trace to a file (e.g. to compare later or re-run retrieval with '
            'different settings), use the "Save calibration" button -- not the plain "Save" '
            'button, which does not handle nested calibration data.')
        self.export_hint_label.setWordWrap(True)

        # ---- retrieval ----
        self.retrieve_button = QtWidgets.QPushButton('Run retrieval')
        self.retrieve_button.setToolTip(
            'Retrieves the most recently generated/acquired trace (COPRA via pypret, 5 '
            'independent restarts). Equivalent to samples/retrieval/tgfrog_retrieval.py, which '
            'also lets you tune --maxiter/--n-starts or re-analyze an exported file later.')

        self.result_trace_error_label = QtWidgets.QLabel('-')
        self.result_gd_label = QtWidgets.QLabel('-')
        self.result_gdd_label = QtWidgets.QLabel('-')
        self.result_tod_label = QtWidgets.QLabel('-')

        results_box = QtWidgets.QGroupBox('Retrieved parameters')
        results_layout = QtWidgets.QFormLayout()
        results_layout.addRow("Trace error G':", self.result_trace_error_label)
        results_layout.addRow('GD:', self.result_gd_label)
        results_layout.addRow('GDD:', self.result_gdd_label)
        results_layout.addRow('TOD:', self.result_tod_label)
        results_box.setLayout(results_layout)

        left_panel = QtWidgets.QVBoxLayout()
        left_panel.addWidget(beam_box)
        left_panel.addWidget(scan_box)
        left_panel.addWidget(self.simulator_box)
        left_panel.addWidget(self.start_button)
        left_panel.addWidget(self.retrieve_button)
        left_panel.addWidget(results_box)
        left_panel.addWidget(self.status_label)
        left_panel.addWidget(self.export_hint_label)
        left_panel.addStretch(1)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(360)

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

        # ---- simulator wiring ----
        self.demo_mode_checkbox.toggled.connect(self.simulator_box.setEnabled)
        self.demo_mode_checkbox.toggled.connect(self._update_demo_button_text)
        self.sim_fwhm_spin.valueChanged.connect(self._update_window_hint)
        self._update_demo_button_text(self.demo_mode_checkbox.isChecked())
        self._update_window_hint()

        """ pyqtgraph's default SI-prefix scaling doesn't make sense for delay in fs or
        wavelength in nm at these magnitudes (shows e.g. a "x0.001" multiplier). """
        self.plot.getAxis('left').enableAutoSIPrefix(False)
        self.plot.getAxis('bottom').enableAutoSIPrefix(False)

        """ Manually setting the view range here (setXRange/setYRange) at various points in
        __init__ never rendered correctly -- the axis ticks stayed compressed into a fraction
        of the plot instead of spanning it. Rather than keep fighting pyqtgraph's own range
        recalculation with a separate manual codepath, seed the plot through set_data() itself,
        the exact same method a real trace uses. This guarantees the idle state renders exactly
        like the active one, just showing zeros. """
        placeholder_delay = np.linspace(-200, 200, 5)
        placeholder_wavelength = np.linspace(700, 900, 5)
        placeholder_data = np.zeros((5, 5))
        self.set_data(placeholder_delay, placeholder_wavelength, placeholder_data)

    def _update_demo_button_text(self, demo_checked):
        self.start_button.setText('Simulate trace' if demo_checked else 'Start TG-FROG scan')

    def _update_window_hint(self):
        """
            Live estimate of the spectral window the TG signal needs for the current FWHM,
            from the Phase 0 relation: TG signal is sqrt(3) narrower in time than the
            fundamental, hence sqrt(3) wider in frequency; combined with the Fourier-limit
            relation for a Gaussian (dnu*dt = 0.441), this gives approximately
            d_lambda_signal[nm] = 1625 / dt[fs] around 800 nm.
        """
        fwhm = self.sim_fwhm_spin.value()
        required_nm = 1625.0 / fwhm if fwhm > 0 else float('inf')
        self.sim_window_hint_label.setText(
            f'-> TG signal needs ~{required_nm:.0f} nm FWHM; good retrieval typically wants '
            f'several times that in the window below.')

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
            """ Without this, the view keeps whatever zoom level it had on the very first
            (2-point) call and never re-fits as the trace grows during a scan, leaving the
            plot mostly black with the actual trace squeezed into a corner. """
            self.plot.getViewBox().autoRange()

    def set_running(self, running):
        """
            Updates button/status state when a scan starts or ends.
            input:
                - running: (bool)
        """
        self.start_button.setEnabled(not running)
        self.status_label.setText('Scanning...' if running else 'Idle.')

    def set_retrieval_running(self, running):
        """
            Updates button/status state while a retrieval is in progress.
            input:
                - running: (bool)
        """
        self.retrieve_button.setEnabled(not running)
        self.retrieve_button.setText('Retrieving...' if running else 'Run retrieval')
        if running:
            self.status_label.setText('Running retrieval (COPRA, up to ~1 min)...')

    def set_retrieval_result(self, result):
        """
            Displays a finished retrieval's results.
            input:
                - result: dict with trace_error, GD, GDD, TOD (fs, fs^2, fs^3), as emitted by
                  TGFROGRetrievalWorker.sendResult
        """
        self.result_trace_error_label.setText(f"{result['trace_error']:.4e}")
        self.result_gd_label.setText(f"{result['GD']:.3f} fs")
        self.result_gdd_label.setText(f"{result['GDD']:.3f} fs^2")
        self.result_tod_label.setText(f"{result['TOD']:.3f} fs^3")
        self.status_label.setText('Retrieval done.')

    def set_retrieval_error(self, message):
        """
            Displays a failed retrieval's error.
            input:
                - message: (str)
        """
        self.status_label.setText(f'Retrieval failed: {message}')
