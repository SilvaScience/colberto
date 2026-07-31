"""
Live 2D view of a spectrograph camera, with the vertical readout controls next to it.

On a spectrograph the horizontal axis of the sensor is wavelength and the vertical axis is position
along the entrance slit, so the signal only occupies the rows where the beam is imaged. This widget
shows where that band actually sits and lets the readout region be set accordingly.

Two modes:
    - Full frame: every sensor row read separately. Slower and noisier per row, used for alignment.
    - Binned: the selected rows are summed on chip into a single row. The read noise is paid once
      instead of once per row, which is what makes weak signals usable for measurements.

Fed straight from the camera worker, deliberately bypassing DataHandling: this is a live diagnostic
view, not measurement data, so it does not go through the 1D acquisition and storage chain.
"""

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CameraDisplay(QtWidgets.QWidget):
    """
        Displays the live camera frame and its vertical profile, and applies the readout region.
    """

    roi_applied = QtCore.pyqtSignal(int, int)  # y0, height

    def __init__(self, spectrometer=None, parent=None):
        """
            Builds the camera view.
            input:
                - spectrometer: a camera driver exposing set_full_frame/set_binned_roi/get_roi
                  (currently Pixis). None leaves the controls disabled until set_spectrometer is called.
                - parent: parent widget
        """
        super(CameraDisplay, self).__init__(parent)
        self.spectrometer = None
        self.last_frame = None
        self._auto_levels_pending = True
        self._last_frame_shape = None

        # ---- image ----
        self.graphLayoutWidget = pg.GraphicsLayoutWidget()
        self.plot = self.graphLayoutWidget.addPlot()
        self.plot.setLabel('bottom', 'Column (wavelength)')
        self.plot.setLabel('left', 'Row (position along slit)')
        self.image = pg.ImageItem(axisOrder='row-major')
        self.plot.addItem(self.image)
        self.histogram = pg.HistogramLUTItem()
        self.histogram.setImageItem(self.image)
        self.graphLayoutWidget.addItem(self.histogram)

        # Lines marking the region that will be binned
        self.region = pg.LinearRegionItem(orientation='horizontal', movable=True)
        self.region.setZValue(10)
        self.plot.addItem(self.region)
        self.region.sigRegionChangeFinished.connect(self.region_dragged)

        # ---- vertical profile ----
        self.profile_plot = pg.PlotWidget()
        self.profile_plot.setLabel('bottom', 'Counts (summed over wavelength)')
        self.profile_plot.setLabel('left', 'Row')
        self.profile_plot.setMaximumWidth(260)
        self.profile_curve = self.profile_plot.plot([], [])

        # ---- controls ----
        self.mode_full_frame = QtWidgets.QRadioButton('Full frame (alignment)')
        self.mode_binned = QtWidgets.QRadioButton('Binned (measurement)')
        self.mode_full_frame.setChecked(True)
        self.y0_spin = QtWidgets.QSpinBox()
        self.y0_spin.setRange(0, 4096)
        self.height_spin = QtWidgets.QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(1)
        self.auto_button = QtWidgets.QPushButton('Find signal band')
        self.apply_button = QtWidgets.QPushButton('Apply readout region')
        self.fit_button = QtWidgets.QPushButton('Fit view')
        self.fit_button.setToolTip(
            'Reset zoom and colour levels to the last frame received.\n'
            'Use this if the image looks empty: after switching between full frame and binned\n'
            'mode the view can stay zoomed on rows that no longer exist in the new frame.')
        self.status_label = QtWidgets.QLabel('No frame received yet.')
        self.status_label.setWordWrap(True)

        controls = QtWidgets.QHBoxLayout()
        mode_box = QtWidgets.QGroupBox('Readout mode')
        mode_layout = QtWidgets.QVBoxLayout()
        mode_layout.addWidget(self.mode_full_frame)
        mode_layout.addWidget(self.mode_binned)
        mode_box.setLayout(mode_layout)
        controls.addWidget(mode_box)

        region_box = QtWidgets.QGroupBox('Rows to bin')
        region_layout = QtWidgets.QHBoxLayout()
        region_layout.addWidget(QtWidgets.QLabel('First row:'))
        region_layout.addWidget(self.y0_spin)
        region_layout.addWidget(QtWidgets.QLabel('Number of rows:'))
        region_layout.addWidget(self.height_spin)
        region_layout.addWidget(self.auto_button)
        region_layout.addWidget(self.apply_button)
        region_layout.addWidget(self.fit_button)
        region_box.setLayout(region_layout)
        controls.addWidget(region_box, stretch=1)

        graphs = QtWidgets.QHBoxLayout()
        graphs.addWidget(self.graphLayoutWidget, stretch=1)
        graphs.addWidget(self.profile_plot)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(controls)
        layout.addLayout(graphs, stretch=1)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        # ---- connections ----
        self.mode_full_frame.toggled.connect(self.mode_changed)
        self.auto_button.clicked.connect(self.find_signal_band)
        self.apply_button.clicked.connect(self.apply_roi)
        self.fit_button.clicked.connect(self.fit_view)
        self.y0_spin.valueChanged.connect(self.spins_changed)
        self.height_spin.valueChanged.connect(self.spins_changed)

        self.set_spectrometer(spectrometer)

    def set_spectrometer(self, spectrometer):
        """
            Attaches the camera whose readout region this widget controls.
            input:
                - spectrometer: camera driver, or None to disable the controls
        """
        self.spectrometer = spectrometer
        supported = spectrometer is not None and hasattr(spectrometer, 'set_binned_roi')
        for widget in (self.mode_full_frame, self.mode_binned, self.y0_spin,
                       self.height_spin, self.auto_button, self.apply_button):
            widget.setEnabled(supported)
        if not supported:
            self.status_label.setText(
                'Active spectrometer does not expose a configurable readout region. '
                'This view only applies to the Pixis camera.')
            return

        sensor_height = int(getattr(spectrometer, 'sensor_height', 256))
        self.y0_spin.setRange(0, max(sensor_height - 1, 0))
        self.height_spin.setRange(1, sensor_height)
        try:
            y0, height, binning = spectrometer.get_roi()
            self.y0_spin.setValue(y0)
            self.height_spin.setValue(height)
            self.mode_binned.setChecked(binning > 1)
            self.mode_full_frame.setChecked(binning == 1)
        except Exception as e:
            logger.warning('Could not read current Pixis ROI: %s', e)
        self.update_region_from_spins()

    @QtCore.pyqtSlot(np.ndarray, float)
    def set_data(self, frame, int_time=None):
        """
            Receives a frame from the camera worker and refreshes the view.
            input:
                - frame (np.ndarray): 1D or 2D camera frame
                - int_time (float): integration time, accepted so this can connect directly to the
                  worker's sendSpectrum signal. Unused.
        """
        frame = np.asarray(frame, dtype=float)
        if frame.ndim == 1:
            frame = frame[np.newaxis, :]
        if frame.size == 0:
            return
        self.last_frame = frame

        """ Re-fit the view whenever the frame shape changes (e.g. switching between full frame and
        binned mode), not just on the very first frame. Otherwise the view can stay zoomed on rows a
        smaller frame no longer has, making it look like nothing is being received. """
        shape_changed = frame.shape != self._last_frame_shape
        self._last_frame_shape = frame.shape
        needs_reset = shape_changed or self._auto_levels_pending

        self.image.setImage(frame, autoLevels=needs_reset)
        if needs_reset:
            self.histogram.setLevels(*self.image.getLevels())
            self._auto_levels_pending = False
        if shape_changed:
            self.plot.getViewBox().autoRange()

        profile = frame.sum(axis=1)
        rows = np.arange(frame.shape[0])
        self.profile_curve.setData(profile, rows)

        if frame.shape[0] == 1:
            self.status_label.setText(
                'Camera is returning a single row: the readout is binned or cropped. '
                'Switch to full frame to see where the signal sits on the sensor.')
        else:
            peak = int(np.argmax(profile - np.median(profile)))
            self.status_label.setText(
                f'Frame {frame.shape[0]} rows x {frame.shape[1]} columns. '
                f'Brightest row: {peak}. Max: {frame.max():.0f} counts.')

    def fit_view(self):
        """
            Resets zoom and colour levels to the last frame received. Use this whenever the image
            looks empty: it removes zoom and windowing as possible causes, leaving "no signal" as
            the only remaining explanation.
        """
        if self.last_frame is None:
            self.status_label.setText('No frame received yet: nothing to fit the view to.')
            return
        self.image.setImage(self.last_frame, autoLevels=True)
        self.histogram.setLevels(*self.image.getLevels())
        self.plot.getViewBox().autoRange()

    def find_signal_band(self, floor_fraction=0.1):
        """
            Sets the row controls from the vertical profile of the last full frame received.
            input:
                - floor_fraction (float): fraction of the peak above baseline delimiting the band
        """
        if self.last_frame is None or self.last_frame.shape[0] < 2:
            self.status_label.setText(
                'Need a full frame first. Select "Full frame" and acquire, then try again.')
            return

        profile = self.last_frame.sum(axis=1)
        contrast = profile - np.median(profile)
        peak_value = contrast.max()
        if peak_value <= 0:
            self.status_label.setText('No vertical structure found: is any light reaching the camera?')
            return

        rows = np.where(contrast >= floor_fraction * peak_value)[0]
        y0, height = int(rows.min()), int(rows.max() - rows.min() + 1)
        self.y0_spin.setValue(y0)
        self.height_spin.setValue(height)

        band = float(profile[y0:y0 + height].sum())
        row0 = float(profile[0])
        gain = band / row0 if row0 > 0 else float('inf')
        self.status_label.setText(
            f'Signal band: rows {y0} to {y0 + height - 1} ({height} rows). '
            f'Binning it collects {gain:.1f}x more signal than row 0 alone.')

    def apply_roi(self):
        """
            Applies the selected readout mode and region to the camera.
        """
        if self.spectrometer is None or not hasattr(self.spectrometer, 'set_binned_roi'):
            return
        try:
            if self.mode_full_frame.isChecked():
                self.spectrometer.set_full_frame()
                self.status_label.setText('Full frame readout applied (alignment mode).')
            else:
                y0, height = self.y0_spin.value(), self.height_spin.value()
                self.spectrometer.set_binned_roi(y0, height)
                self.status_label.setText(
                    f'Binned readout applied: rows {y0} to {y0 + height - 1} summed on chip.')
                self.roi_applied.emit(y0, height)
            self._auto_levels_pending = True
        except Exception as e:
            logger.error('Failed to apply Pixis ROI: %s', e)
            self.status_label.setText(f'Could not apply readout region: {e}')

    def mode_changed(self):
        """
            Enables the row controls only in binned mode.
        """
        binned = self.mode_binned.isChecked()
        for widget in (self.y0_spin, self.height_spin):
            widget.setEnabled(binned)
        self.region.setVisible(binned)

    def spins_changed(self):
        """
            Keeps the region overlay in step with the spin boxes.
        """
        self.update_region_from_spins()

    def update_region_from_spins(self):
        """
            Redraws the region overlay from the current row controls.
        """
        y0 = self.y0_spin.value()
        height = self.height_spin.value()
        self.region.blockSignals(True)
        self.region.setRegion([y0, y0 + height])
        self.region.blockSignals(False)

    def region_dragged(self):
        """
            Updates the row controls when the region overlay is dragged on the image.
        """
        lo, hi = self.region.getRegion()
        y0 = max(int(round(lo)), 0)
        height = max(int(round(hi - lo)), 1)
        self.y0_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.y0_spin.setValue(y0)
        self.height_spin.setValue(height)
        self.y0_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
