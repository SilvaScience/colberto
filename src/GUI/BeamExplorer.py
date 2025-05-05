from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5 import QtCore
import sys


class BeamExplorer(QWidget):
    """
        Display the properties of the beams currently held in the provided DataHandler
    """
    request_beams= QtCore.pyqtsignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.label = QLabel("Beam explorer")
        self.layout.addWidget(self.label)
        self.setLayout(layout)
    
    def receive_beams(self,beamDict):
        """
            Handle the beams sent from DataHandler
        """
        self.beams=beamDict

    def create_beam_display(self):
        """
            Appends a beam display to the current layout
        """
        sub_layout=QVBoxLayout()
        sub_layout.plot=pg.plot()