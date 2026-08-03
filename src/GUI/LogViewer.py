"""
Live viewer for the application's log file (main.log), opened from the File menu.

logging.basicConfig(filename='main.log', ...) in main.py writes to a path relative to whatever the
current working directory was when the app was launched, so the file itself can be non-obvious to
find by hand (repo root if launched as `python src/main.py` from there, src/ if launched from
inside it, etc.). This dialog resolves and displays that path, shows the current content, and polls
the file so it behaves like `tail -f` while left open -- useful for watching what a driver logs
while reproducing a problem, without alt-tabbing to a text editor and losing track of the file.
"""

from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui


class LogViewer(QtWidgets.QDialog):
    """
        Read-only, auto-refreshing view of a log file. Non-modal: stays open and updating while the
        rest of the interface is used normally.
    """

    def __init__(self, log_path, parent=None, poll_interval_ms=1000):
        """
            Builds the viewer.
            input:
                - log_path (str or Path): path to the log file to display
                - parent: parent widget
                - poll_interval_ms (int): how often to check the file for new content
        """
        super(LogViewer, self).__init__(parent)
        self.log_path = Path(log_path).resolve()
        self._last_size = -1

        self.setWindowTitle('Log')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinMaxButtonsHint)
        self.resize(900, 500)

        self.path_label = QtWidgets.QLabel(str(self.log_path))
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.path_label.setStyleSheet('color: gray;')

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        font = QtGui.QFont('Consolas')
        font.setStyleHint(QtGui.QFont.Monospace)
        self.text.setFont(font)

        self.follow_checkbox = QtWidgets.QCheckBox('Follow (auto-scroll)')
        self.follow_checkbox.setChecked(True)
        self.refresh_button = QtWidgets.QPushButton('Refresh now')
        self.clear_view_button = QtWidgets.QPushButton('Clear view')
        self.clear_view_button.setToolTip('Clears this window only. Does not touch the log file.')

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.follow_checkbox)
        controls.addStretch(1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.clear_view_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.path_label)
        layout.addWidget(self.text, stretch=1)
        layout.addLayout(controls)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(self.reload)
        self.clear_view_button.clicked.connect(self.text.clear)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(poll_interval_ms)
        self.timer.timeout.connect(self.poll)

    def showEvent(self, event):
        """ Refreshes and (re)starts polling whenever the window becomes visible. """
        super(LogViewer, self).showEvent(event)
        self.reload()
        self.timer.start()

    def hideEvent(self, event):
        """ Stops polling while the window is closed/hidden, so it doesn't run in the background. """
        self.timer.stop()
        super(LogViewer, self).hideEvent(event)

    def reload(self):
        """
            Reads the whole file and replaces the view with its content.
        """
        try:
            content = self.log_path.read_text(encoding='utf-8', errors='replace')
        except FileNotFoundError:
            content = f'(no log file yet at {self.log_path})'
        except OSError as e:
            content = f'(could not read {self.log_path}: {e})'
        self.text.setPlainText(content)
        self._last_size = self._current_size()
        self._scroll_to_bottom()

    def poll(self):
        """
            Checks whether the file grew since the last read and appends only the new part, rather
            than reloading and re-rendering the whole file on every tick.
        """
        size = self._current_size()
        if size == self._last_size:
            return
        if size < 0:
            return  # file (still) doesn't exist or isn't readable: nothing to poll
        if self._last_size < 0 or size < self._last_size:
            # either the file just appeared (nothing valid to seek from yet) or it was
            # truncated/replaced (e.g. rotated): read it from the start instead of seeking
            self.reload()
            return
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(self._last_size)
                new_content = f.read()
        except OSError:
            return
        self._last_size = size
        if not new_content:
            return
        was_following = self.follow_checkbox.isChecked()
        self.text.appendPlainText(new_content.rstrip('\n'))
        if was_following:
            self._scroll_to_bottom()

    def _current_size(self):
        try:
            return self.log_path.stat().st_size
        except OSError:
            return -1

    def _scroll_to_bottom(self):
        scrollbar = self.text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
