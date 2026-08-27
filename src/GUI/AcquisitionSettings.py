"""
Acquisition settings for the Stresing camera, expressed as a mode rather than as raw registers.

The board is configured through two trigger registers, sti (what starts one readout) and bti (what
starts one block of readouts). They share the numbering of the external inputs but diverge above 4,
each has a timer that only applies in one of its modes, and both are counts of microseconds. Shown
as eight independent spin boxes this is unusable: nothing says that Scan_Timer is ignored unless
Scan_Trig is exactly 4, and nothing says what the numbers mean.

This widget exposes the three setups the experiment actually uses -- the board running on its own
timer, one readout per laser pulse, and blocks gated by a chopper -- and derives sti/bti from that.
Timers are entered with a unit and their effect is shown in Hz and in total acquisition time.
"""

from PyQt5 import QtWidgets, QtCore
from functools import partial
import logging

from drivers.Stresing import (TRIGGER_INPUTS, CHOPPER_INPUTS,
                              CONTINUOUS, EXTERNAL, CHOPPER)

logger = logging.getLogger(__name__)

UNITS_US = {'us': 1, 'ms': 1000, 's': 1000000}

""" Parameters this panel already presents in a friendlier form, and which must therefore not be
repeated as raw spin boxes in the camera group. """
PANEL_OWNED = ('No_Sample', 'No_Block', 'Scan_Trig', 'Block_Trig', 'Scan_Timer', 'Block_Timer')


class AcquisitionSettings(QtWidgets.QWidget):
    """
        Trigger and timing controls for a camera exposing set_acquisition_mode().
    """

    settings_applied = QtCore.pyqtSignal()

    def __init__(self, spectrometer=None, parent=None):
        """
            Builds the panel.
            input:
                - spectrometer: camera driver exposing set_acquisition_mode/get_acquisition_mode
                  (currently Stresing). None leaves the controls disabled.
                - parent: parent widget
        """
        super(AcquisitionSettings, self).__init__(parent)
        self.spectrometer = None
        self.monochromator = None
        """ Set by the main window to a callable telling whether a measurement is running. Applying
        re-initialises the measurement on the board from the GUI thread, which would block the
        interface if the board were still busy with the previous acquisition. """
        self.is_busy = None

        # ---- mode ----
        self.mode_continuous = QtWidgets.QRadioButton('Continuous (internal timer)')
        self.mode_continuous.setToolTip('The board triggers itself on its internal timer.\n'
                                        'Use this to check alignment or to test without the laser.')
        self.mode_external = QtWidgets.QRadioButton('Synchronised to laser')
        self.mode_external.setToolTip('One readout per pulse on a trigger input of the PCIe board.')
        self.mode_chopper = QtWidgets.QRadioButton('Chopper')
        self.mode_chopper.setToolTip('Blocks are gated by a chopper signal, for shot to shot\n'
                                     'referencing between pumped and unpumped spectra.')
        self.mode_continuous.setChecked(True)

        self.mode_box = QtWidgets.QGroupBox('Trigger mode')
        mode_layout = QtWidgets.QVBoxLayout()
        for widget in (self.mode_continuous, self.mode_external, self.mode_chopper):
            mode_layout.addWidget(widget)
            widget.toggled.connect(self.mode_changed)
        mode_layout.addStretch(1)
        self.mode_box.setLayout(mode_layout)

        # ---- timing ----
        self.scan_interval = QtWidgets.QDoubleSpinBox()
        self.scan_interval.setRange(0.001, 1000000)
        self.scan_interval.setDecimals(2)
        self.scan_interval.setValue(10)
        self.scan_unit = QtWidgets.QComboBox()
        self.scan_unit.addItems(list(UNITS_US.keys()))
        self.scan_unit.setCurrentText('ms')
        self.scan_rate_label = QtWidgets.QLabel()

        self.block_interval = QtWidgets.QDoubleSpinBox()
        self.block_interval.setRange(0.001, 1000000)
        self.block_interval.setDecimals(2)
        self.block_interval.setValue(300)
        self.block_unit = QtWidgets.QComboBox()
        self.block_unit.addItems(list(UNITS_US.keys()))
        self.block_unit.setCurrentText('ms')

        self.timing_box = QtWidgets.QGroupBox('Timing')
        timing_layout = QtWidgets.QGridLayout()
        timing_layout.addWidget(QtWidgets.QLabel('Spectrum interval:'), 0, 0)
        timing_layout.addWidget(self.scan_interval, 0, 1)
        timing_layout.addWidget(self.scan_unit, 0, 2)
        timing_layout.addWidget(self.scan_rate_label, 0, 3)
        timing_layout.addWidget(QtWidgets.QLabel('Block interval:'), 1, 0)
        timing_layout.addWidget(self.block_interval, 1, 1)
        timing_layout.addWidget(self.block_unit, 1, 2)
        timing_layout.setColumnStretch(3, 1)
        self.timing_box.setLayout(timing_layout)

        # ---- trigger source ----
        self.trigger_input = QtWidgets.QComboBox()
        self.trigger_input.addItems(list(TRIGGER_INPUTS.keys()))
        self.trigger_input.setToolTip('Connector on the PCIe board carrying the trigger.')
        self.chopper_input = QtWidgets.QComboBox()
        self.chopper_input.addItems(list(CHOPPER_INPUTS.keys()))
        self.scan_on_timer = QtWidgets.QCheckBox('Read out on internal timer')
        self.scan_on_timer.setToolTip('Chopper gates the blocks, while the readouts inside a block\n'
                                      'run on the internal timer instead of a trigger input.')
        self.timeout = QtWidgets.QDoubleSpinBox()
        self.timeout.setRange(0.1, 3600)
        self.timeout.setDecimals(1)
        self.timeout.setValue(5)
        self.timeout.setSuffix(' s')
        self.timeout.setToolTip('Give up if no scan arrives within this time, instead of waiting\n'
                                'forever on a trigger that is not coming.')

        self.source_box = QtWidgets.QGroupBox('Trigger source')
        source_layout = QtWidgets.QGridLayout()
        source_layout.addWidget(QtWidgets.QLabel('Input:'), 0, 0)
        source_layout.addWidget(self.trigger_input, 0, 1)
        source_layout.addWidget(self.chopper_label(), 1, 0)
        source_layout.addWidget(self.chopper_input, 1, 1)
        source_layout.addWidget(self.scan_on_timer, 2, 0, 1, 2)
        source_layout.addWidget(QtWidgets.QLabel('Timeout:'), 3, 0)
        source_layout.addWidget(self.timeout, 3, 1)
        source_layout.setColumnStretch(2, 1)
        self.source_box.setLayout(source_layout)

        # ---- structure ----
        self.scans_per_block = QtWidgets.QSpinBox()
        self.scans_per_block.setRange(6, 100000)
        self.scans_per_block.setValue(10)
        self.scans_per_block.setToolTip('Readouts averaged into one spectrum (nos).')
        self.blocks = QtWidgets.QSpinBox()
        self.blocks.setRange(1, 100000)
        self.blocks.setValue(1)
        self.blocks.setToolTip('Number of blocks (nob).')

        self.structure_box = QtWidgets.QGroupBox('Acquisition structure')
        structure_layout = QtWidgets.QGridLayout()
        structure_layout.addWidget(QtWidgets.QLabel('Spectra / block:'), 0, 0)
        structure_layout.addWidget(self.scans_per_block, 0, 1)
        structure_layout.addWidget(QtWidgets.QLabel('Blocks:'), 1, 0)
        structure_layout.addWidget(self.blocks, 1, 1)
        structure_layout.setColumnStretch(2, 1)
        self.structure_box.setLayout(structure_layout)

        # ---- monochromator ----
        self.center_wavelength = QtWidgets.QDoubleSpinBox()
        self.center_wavelength.setRange(200, 1100)
        self.center_wavelength.setDecimals(2)
        self.center_wavelength.setSuffix(' nm')
        self.center_wavelength.setToolTip('Wavelength at the centre of the sensor. Moves the grating.')
        self.grating_choice = QtWidgets.QComboBox()

        """ The exit mirror decides which camera receives the light at all, which is worth naming
        after the cameras rather than after the mirror positions. Checked on the bench with a HeNe:
        front sends the beam to the Pixis, side to the Stresing. ?MIR reports 0 and 1 respectively. """
        self.exit_port = QtWidgets.QComboBox()
        self.exit_port.addItem('Stresing (side)', 1)
        self.exit_port.addItem('Pixis (front)', 0)
        self.exit_port.setToolTip('Which exit port of the spectrograph the light leaves by.\n'
                                  'The camera on the other port sees nothing.')

        self.apply_mono_button = QtWidgets.QPushButton('Move optics')
        self.mono_status = QtWidgets.QLabel()
        self.mono_status.setWordWrap(True)

        self.mono_box = QtWidgets.QGroupBox('Monochromator')
        mono_layout = QtWidgets.QGridLayout()
        mono_layout.addWidget(QtWidgets.QLabel('Wavelength:'), 0, 0)
        mono_layout.addWidget(self.center_wavelength, 0, 1)
        mono_layout.addWidget(QtWidgets.QLabel('Grating:'), 1, 0)
        mono_layout.addWidget(self.grating_choice, 1, 1)
        mono_layout.addWidget(QtWidgets.QLabel('Light to:'), 2, 0)
        mono_layout.addWidget(self.exit_port, 2, 1)
        mono_layout.addWidget(self.apply_mono_button, 3, 0, 1, 2)
        mono_layout.addWidget(self.mono_status, 4, 0, 1, 2)
        mono_layout.setColumnStretch(2, 1)
        self.mono_box.setLayout(mono_layout)

        # ---- camera parameters ----
        """ The camera's own settings, built from the driver's parameter_display_dict so this works
        for any spectrometer without naming its parameters here. The Hardware tree shows the same
        values read-only: control belongs next to the acquisition settings it affects, not in a tree
        shared with every other device. """
        self.camera_box = QtWidgets.QGroupBox('Camera')
        self.camera_layout = QtWidgets.QGridLayout()
        self.camera_box.setLayout(self.camera_layout)
        self.camera_widgets = {}
        """ Set by the main window so a change made here also reaches the value it records with the
        data and the read-only row in the tree. """
        self.parameter_changed = None

        # ---- summary and actions ----
        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        self.registers_label = QtWidgets.QLabel()
        self.registers_label.setWordWrap(True)
        self.registers_label.setToolTip('What this writes to the board, in the vocabulary of\n'
                                        'the active site configuration and the Stresing documentation.')
        self.apply_button = QtWidgets.QPushButton('Apply')
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)

        """ Minimum widths so the panel asks the splitter for the room it needs. Squeezed below these
        the radio labels and combo entries are clipped to nothing, which is what the first version of
        this layout did. """
        for widget in (self.trigger_input, self.chopper_input, self.grating_choice):
            widget.setMinimumWidth(130)
            widget.setMaximumWidth(170)
        for widget in (self.scan_interval, self.block_interval, self.scans_per_block,
                       self.blocks, self.timeout, self.center_wavelength):
            widget.setMinimumWidth(80)
            widget.setMaximumWidth(110)
        for widget in (self.scan_unit, self.block_unit):
            widget.setMinimumWidth(60)

        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.apply_button)

        """ Two columns rather than one tall stack: the panel shares its row with the camera view, so
        it has to stay short enough to need no scrolling, and it is the width that is available. Boxes
        that are only shown in some modes sit in the left column, so hiding them does not leave a gap
        in the middle of the panel.

        status_label used to sit at the very bottom, sharing a row with apply_button after every
        other box -- for the message it shows most often ("Active spectrometer has no configurable
        trigger", set as soon as a non-Stresing camera is attached, in set_spectrometer below), that
        put it past everything it's actually explaining. Moved up to its own row right under the
        trigger boxes it describes, still above the camera box so it never overlaps it. """
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.mode_box, 0, 0, 2, 1)
        layout.addWidget(self.timing_box, 0, 1)
        layout.addWidget(self.structure_box, 1, 1)
        layout.addWidget(self.source_box, 2, 0)
        layout.addWidget(self.mono_box, 2, 1)
        layout.addWidget(self.status_label, 3, 0, 1, 2)
        layout.addWidget(self.camera_box, 4, 0, 1, 2)
        layout.addWidget(self.summary_label, 5, 0, 1, 2)
        layout.addWidget(self.registers_label, 6, 0, 1, 2)
        layout.addLayout(actions, 7, 0, 1, 2)
        layout.setRowStretch(8, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # ---- connections ----
        self.apply_button.clicked.connect(self.apply_settings)
        self.apply_mono_button.clicked.connect(self.apply_monochromator)
        for widget in (self.scan_interval, self.block_interval, self.scans_per_block, self.blocks):
            widget.valueChanged.connect(self.refresh_summary)
        for widget in (self.scan_unit, self.block_unit, self.trigger_input, self.chopper_input):
            widget.currentIndexChanged.connect(self.refresh_summary)
        self.scan_on_timer.toggled.connect(self.refresh_summary)

        self.set_spectrometer(spectrometer)

    def chopper_label(self):
        """
            Builds the chopper row label, kept as a method so it can be hidden with its combo box.
        """
        self._chopper_label = QtWidgets.QLabel('Chopper:')
        return self._chopper_label

    def set_spectrometer(self, spectrometer):
        """
            Attaches the camera this panel configures, and reads its current setup back into the
            controls.
            input:
                - spectrometer: camera driver, or None to disable the panel
        """
        self.spectrometer = spectrometer
        """ Built for every camera, including those with no configurable trigger: the trigger boxes
        below may end up disabled, the camera's own settings stay usable. """
        self.build_camera_parameters(spectrometer)

        supported = spectrometer is not None and hasattr(spectrometer, 'set_acquisition_mode')
        """ Only the camera side is disabled: the monochromator is shared by every spectrometer and
        stays usable whichever camera is selected. """
        for box in (self.mode_box, self.timing_box, self.source_box, self.structure_box):
            box.setEnabled(supported)
        self.apply_button.setEnabled(supported)
        if not supported:
            self.status_label.setText('Active spectrometer has no configurable trigger. '
                                      'This tab applies to the Stresing camera.')
            return

        try:
            current = spectrometer.get_acquisition_mode()
        except Exception as e:
            logger.warning('Could not read the Stresing trigger setup: %s', e)
            self.mode_changed()
            return

        self.mode_continuous.setChecked(current['mode'] == CONTINUOUS)
        self.mode_external.setChecked(current['mode'] == EXTERNAL)
        self.mode_chopper.setChecked(current['mode'] == CHOPPER)
        self.set_interval(self.scan_interval, self.scan_unit, current['scan_interval_us'])
        self.set_interval(self.block_interval, self.block_unit, current['block_interval_us'])
        self.scan_on_timer.setChecked(current['scan_trigger'] == 'timer')
        if current['scan_trigger'] in TRIGGER_INPUTS:
            self.trigger_input.setCurrentText(current['scan_trigger'])
        self.chopper_input.setCurrentText(current['chopper'])
        self.timeout.setValue(current['timeout_s'])
        self.scans_per_block.setValue(getattr(spectrometer, 'sample', 10))
        self.blocks.setValue(getattr(spectrometer, 'block', 1))
        self.mode_changed()

    def build_camera_parameters(self, spectrometer):
        """
            Rebuilds the camera controls from the driver's own parameter declaration.
            input:
                - spectrometer: camera driver, or None to leave the group empty
        """
        while self.camera_layout.count():
            widget = self.camera_layout.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self.camera_widgets = {}

        display = getattr(spectrometer, 'parameter_display_dict', None) or {}
        row = 0
        for name, info in display.items():
            if name in PANEL_OWNED:
                continue
            spin = QtWidgets.QDoubleSpinBox()
            spin.setMinimumWidth(90)
            spin.setMaximumWidth(140)
            for key, setter in (('unit', spin.setSuffix), ('max', spin.setMaximum),
                                ('min', spin.setMinimum), ('val', spin.setValue)):
                try:
                    setter(info[key])
                except (KeyError, TypeError):
                    pass
            if info.get('read'):
                """ A reading, not a setting: shown so the value is visible next to the controls that
                depend on it, but the driver has nothing to set it to. """
                spin.setReadOnly(True)
                spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            else:
                spin.editingFinished.connect(partial(self.apply_camera_parameter, name))
            """ All on row 0 instead of wrapping every 2 items: with the 3 Stresing parameters
            (int_time, binning, avg_scan) that used to mean 2 on one row and 1 alone on the next. """
            self.camera_layout.addWidget(QtWidgets.QLabel('%s:' % name), 0, row * 2)
            self.camera_layout.addWidget(spin, 0, row * 2 + 1)
            self.camera_widgets[name] = spin
            row += 1

        self.camera_layout.setColumnStretch(row * 2, 1)
        self.camera_box.setVisible(bool(self.camera_widgets))

    def apply_camera_parameter(self, name):
        """
            Pushes one camera parameter to the driver.
            input:
                - name (str): parameter name as the driver declares it
        """
        if self.spectrometer is None or name not in self.camera_widgets:
            return
        if callable(self.is_busy) and self.is_busy():
            self.status_label.setText('A measurement is running. Stop it before changing %s.' % name)
            return
        value = self.camera_widgets[name].value()
        try:
            self.spectrometer.set_parameter(name, value)
        except Exception as e:
            logger.error('Could not set %s: %s', name, e)
            self.status_label.setText('Could not set %s: %s' % (name, e))
            return
        self.status_label.setText('%s set to %g.' % (name, value))
        if callable(self.parameter_changed):
            self.parameter_changed(name, value)

    def set_monochromator(self, monochromator):
        """
            Attaches the monochromator whose grating and centre wavelength this panel drives.
            input:
                - monochromator: driver exposing set_parameter('central_wave'/'grating'), or None
        """
        self.monochromator = monochromator
        supported = monochromator is not None and hasattr(monochromator, 'set_parameter')
        self.mono_box.setEnabled(supported)
        if not supported:
            self.mono_status.setText('No monochromator connected.')
            return

        """ grating_densities is read back from the instrument and its last entries can be padding
        rather than real gratings, so only plausible groove densities are offered. """
        self.grating_choice.clear()
        for index, density in enumerate(getattr(monochromator, 'grating_densities', []), start=1):
            if density >= 50:
                self.grating_choice.addItem('%d  (%d lines/mm)' % (index, density), index)

        current = int(getattr(monochromator, 'grating', 1))
        position = self.grating_choice.findData(current)
        if position >= 0:
            self.grating_choice.setCurrentIndex(position)
        self.center_wavelength.setValue(float(getattr(monochromator, 'center_wl', 0.0)))

        position = self.exit_port.findData(int(getattr(monochromator, 'mirror', 1)))
        if position >= 0:
            self.exit_port.setCurrentIndex(position)
        self.mono_status.setText('')

    def apply_monochromator(self):
        """
            Moves the grating and the centre wavelength. Both are slow mechanical moves, so they are
            applied on their own button rather than with the trigger settings.
        """
        if self.monochromator is None or not hasattr(self.monochromator, 'set_parameter'):
            return
        if callable(self.is_busy) and self.is_busy():
            self.mono_status.setText('A measurement is running. Stop it before moving the grating.')
            return
        grating = self.grating_choice.currentData()
        port = self.exit_port.currentData()
        try:
            """ Only moved when it actually changes: both are slow mechanical moves, and the grating
            in particular takes seconds to settle. """
            if grating is not None and grating != int(getattr(self.monochromator, 'grating', 0)):
                self.monochromator.set_parameter('grating', grating)
            self.monochromator.set_parameter('central_wave', self.center_wavelength.value())
            if port is not None and port != int(getattr(self.monochromator, 'mirror', -1)):
                self.monochromator.set_parameter('mirror', port)
        except Exception as e:
            logger.error('Could not move the monochromator: %s', e)
            self.mono_status.setText('Could not move: %s' % e)
            return
        self.mono_status.setText('%.2f nm, light to %s.'
                                 % (self.center_wavelength.value(), self.exit_port.currentText()))
        self.settings_applied.emit()

    def set_interval(self, spin, unit, microseconds):
        """
            Fills an interval control with the largest unit that keeps the number readable.
            input:
                - spin (QDoubleSpinBox): value control
                - unit (QComboBox): unit control
                - microseconds (int): interval to display
        """
        microseconds = max(float(microseconds), 0.001)
        for name in ('s', 'ms', 'us'):
            if microseconds >= UNITS_US[name]:
                unit.setCurrentText(name)
                spin.setValue(microseconds / UNITS_US[name])
                return
        unit.setCurrentText('us')
        spin.setValue(microseconds)

    def current_mode(self):
        """
            Returns the selected mode.
        """
        if self.mode_external.isChecked():
            return EXTERNAL
        if self.mode_chopper.isChecked():
            return CHOPPER
        return CONTINUOUS

    def scan_interval_us(self):
        """
            Returns the readout interval in microseconds.
        """
        return self.scan_interval.value() * UNITS_US[self.scan_unit.currentText()]

    def block_interval_us(self):
        """
            Returns the block interval in microseconds.
        """
        return self.block_interval.value() * UNITS_US[self.block_unit.currentText()]

    def readouts_on_timer(self):
        """
            True when the readouts themselves run on the internal timer, which is always the case in
            continuous mode and optional under a chopper.
        """
        mode = self.current_mode()
        return mode == CONTINUOUS or (mode == CHOPPER and self.scan_on_timer.isChecked())

    def mode_changed(self):
        """
            Shows only the controls the selected mode actually uses. The timers are hidden rather
            than greyed when the board ignores them, so no value on screen is a value with no effect.
        """
        mode = self.current_mode()
        on_timer = self.readouts_on_timer()

        self.timing_box.setVisible(on_timer or mode == CONTINUOUS)
        self.scan_interval.setEnabled(on_timer)
        self.scan_unit.setEnabled(on_timer)
        self.scan_rate_label.setEnabled(on_timer)
        self.block_interval.setEnabled(mode == CONTINUOUS)
        self.block_unit.setEnabled(mode == CONTINUOUS)

        self.source_box.setVisible(mode != CONTINUOUS)
        self.trigger_input.setVisible(mode == EXTERNAL or (mode == CHOPPER and not on_timer))
        self._chopper_label.setVisible(mode == CHOPPER)
        self.chopper_input.setVisible(mode == CHOPPER)
        self.scan_on_timer.setVisible(mode == CHOPPER)

        self.refresh_summary()

    def refresh_summary(self):
        """
            Recomputes the derived readouts: readout rate, total number of spectra, expected
            duration, and the registers this will write.
        """
        mode = self.current_mode()
        nos, nob = self.scans_per_block.value(), self.blocks.value()

        scan_us = self.scan_interval_us()
        if self.readouts_on_timer() and scan_us > 0:
            self.scan_rate_label.setText('= %d Hz' % round(1000000.0 / scan_us))
        else:
            self.scan_rate_label.setText('')

        if mode == CONTINUOUS:
            total_us = nos * scan_us * nob
            duration = ('%.1f s' % (total_us / 1000000.0) if total_us >= 1000000
                        else '%d ms' % round(total_us / 1000.0))
            self.summary_label.setText('This acquisition: %d spectra averaged, about %s.'
                                       % (nos * nob, duration))
        elif mode == EXTERNAL:
            self.summary_label.setText(
                'This acquisition: %d spectra averaged, at the rate of the laser. '
                'Needs %d trigger pulses on input %s.'
                % (nos * nob, nos * nob, self.trigger_input.currentText()))
        else:
            self.summary_label.setText(
                'This acquisition: %d spectra averaged, %d block%s gated by the chopper on %s.'
                % (nos * nob, nob, '' if nob == 1 else 's', self.chopper_input.currentText()))

        self.registers_label.setText('Writes: %s' % self.registers_preview(mode, nos, nob))

    def registers_preview(self, mode, nos, nob):
        """
            Describes the registers the current selection maps to, in the vocabulary of
            the active site configuration.
            input:
                - mode (str): selected mode
                - nos (int): spectra per block
                - nob (int): number of blocks
        """
        if mode == CONTINUOUS:
            return ('sti=4, stimer=%d, bti=4, btimer=%d, nos=%d, nob=%d'
                    % (round(self.scan_interval_us()), round(self.block_interval_us()), nos, nob))
        if mode == EXTERNAL:
            source = TRIGGER_INPUTS[self.trigger_input.currentText()]
            return 'sti=%d, bti=%d, nos=%d, nob=%d (timers unused)' % (source, source, nos, nob)
        bti = CHOPPER_INPUTS[self.chopper_input.currentText()]
        if self.scan_on_timer.isChecked():
            return ('sti=4, stimer=%d, bti=%d, nos=%d, nob=%d'
                    % (round(self.scan_interval_us()), bti, nos, nob))
        sti = TRIGGER_INPUTS[self.trigger_input.currentText()]
        return 'sti=%d, bti=%d, nos=%d, nob=%d (timers unused)' % (sti, bti, nos, nob)

    def apply_settings(self):
        """
            Pushes the selection to the camera.
        """
        if self.spectrometer is None or not hasattr(self.spectrometer, 'set_acquisition_mode'):
            return
        if callable(self.is_busy) and self.is_busy():
            self.status_label.setText('A measurement is running. Stop it before changing the trigger.')
            return
        mode = self.current_mode()
        scan_trigger = ('timer' if mode == CHOPPER and self.scan_on_timer.isChecked()
                        else self.trigger_input.currentText())
        try:
            self.spectrometer.set_parameter('No_Sample', self.scans_per_block.value())
            self.spectrometer.set_parameter('No_Block', self.blocks.value())
            self.spectrometer.set_acquisition_mode(
                mode,
                scan_trigger=scan_trigger,
                chopper=self.chopper_input.currentText(),
                scan_interval_us=self.scan_interval_us(),
                block_interval_us=self.block_interval_us(),
                timeout_s=self.timeout.value())
        except Exception as e:
            logger.error('Could not apply the Stresing acquisition settings: %s', e)
            self.status_label.setText('Could not apply: %s' % e)
            return
        self.status_label.setText('Applied.')
        self.settings_applied.emit()
