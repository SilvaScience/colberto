from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QTableWidget
from PyQt5 import QtCore,uic
import sys
import os
from pathlib import Path

class BeamExplorer(QWidget):
    """
        Display the properties of the beams currently held in the provided DataHandler
    """
    request_beams= QtCore.pyqtSignal()
    beams_changed=QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setWindowTitle("Beam explorer")
        self.beamwidget=BeamWidget()
        self.layout.addWidget(self.beamwidget)
        self.setLayout(self.layout)
    
    def receive_beams(self,beamDict):
        """
            Handle the beams sent from DataHandler
        """
        self.beams=beamDict
        # Counts the number of beams and compares it to the number of beam displays
            # Create additional beam displays if required
        # Populates all displays with information

    def create_beam_display(self):
        """
            Appends a beam display to the current layout
        """
        sub_layout=QVBoxLayout()

        table=QTableWidget()
        table.setRowCount(1)
        table.setColumnCount(4)
        sub_layout.addWidget(table)
        #sub_layout.addWidget(pg.plot)

class BeamWidget(QWidget):
    """
        Instantiate the Widget displaying a single beam's properties. 
    """
    beam_changed=QtCore.pyqtSignal()

    def __init__(self):
        """
            Loads the widget from a UI file.
        """
        super(BeamWidget,self).__init__()
        project_folder=os.path.dirname(sys.modules['__main__'].__file__)
        uic.loadUi(Path(project_folder,r'GUI/beam_explorer.ui'), self)