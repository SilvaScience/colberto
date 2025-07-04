from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QTableWidget,QSpinBox,QCheckBox, QTableWidgetItem
from PyQt5 import QtCore,uic
import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
class BeamExplorer(QWidget):
    """
        Display the properties of the beams currently held in the provided DataHandler
    """
    request_beams= QtCore.pyqtSignal()
    beams_changed=QtCore.pyqtSignal(object)
    
    def __init__(self,beamDict):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setWindowTitle("Beam explorer")
        self.beamWidgets=[]
        self.receive_beams(beamDict)
    
    def receive_beams(self,beamDict):
        """
            Handle the beams sent from DataHandler
        """
        self.beamDict=beamDict
        for beamWidget,beam_name in zip(self.beamWidgets,self.beamDict):
            beamWidget.import_beam(beam_name,self.beamDict[beam_name])
        for beam_name in self.beamDict:
            if not beam_name in [beamWidget.name for beamWidget in self.beamWidgets]:
                new_beam_widget=BeamWidget(beam_name,self.beamDict[beam_name])
                self.beamWidgets.append(new_beam_widget)
                self.layout.addWidget(new_beam_widget)
        self.setLayout(self.layout)
        
    def update_beam(self,beam_key_value):
        """
            Updates a beam when updated from BeamWidget
            input:
                - beam_key_value: tuple (str, Beam) consisting of beam's name and the beam itself
        """
        name,beam=beam_key_value
        self.beamDict[name]=beam
        self.beams_changed.emit(self.beamDict)


class BeamWidget(QWidget):
    """
        Instantiate the Widget displaying a single beam's properties. 
    """
    beam_changed=QtCore.pyqtSignal(object)

    def __init__(self,name,beam):
        """
            Loads the widget from a UI file.
            input:
                - name (str): The name of the beam
                - beam (Beam): The Beam itself
        """
        super(BeamWidget,self).__init__()
        project_folder=os.path.dirname(sys.modules['__main__'].__file__)
        uic.loadUi(Path(project_folder,r'GUI/beam_explorer.ui'), self)
        # Load components
        self.apply_pushbutton=self.findChild(QPushButton,'apply_pushbutton')
        self.beam_label=self.findChild(QLabel,'beam_label')
        self.grating_period=self.findChild(QSpinBox,'grating_period_value')
        self.delimiter_table=self.findChild(QTableWidget,'delimiter_table_widget')
        self.phase_coeff_table=self.findChild(QTableWidget,'phase_coeff_table')
        self.relative_checkbox=self.findChild(QCheckBox,'relative_checkbox')
        self.import_beam(name,beam)
    
    def import_beam(self,name,beam):
        '''
            Updates the beam into the widget
        '''
        self.beam=beam
        self.name=name
        self.update_display_from_beam()

    def update_display_from_beam(self):
        """
            Update the displayed parameters from the values stored in the beam attribute of the widget
        """
        self.beam_label.setText(self.name)
        self.grating_period.setValue(self.beam.get_gratingPeriod())
        [self.delimiter_table_widget.setItem(0,i,QTableWidgetItem(value)) for i,value in enumerate(self.beam.get_beamVerticalDelimiters())]
        logger.info(self.beam.get_gratingPeriod())
        #[self.delimiter_table_widget.setItem(0,i,QTableWidgetItem(value)) for i,value in enumerate(self.beam.get_beamVerticalDelimiters())]
        #[self.delimiter_table_widget.item(1,i).setText(value) for i,value in enumerate(self.beam.get_beamHorizontalDelimiters())]
        #[self.phase_coeff_table.item(0,i).setText(coeff) for i,coeff in enumerate(self.beam.get_optimalPhase().coeff)]
        if self.relative_checkbox.isChecked():
            mode='relative'
        else:
            mode='absolute'
        #[self.phase_coeff_table.item(1,i).setText(coeff) for i,coeff in enumerate(self.beam.get_currentPhase(mode=mode).coeff)]
    def plot_phase(self):
        '''
            Plots the current phase of the beam either relative to the compression or absolute
        '''
    def update_beam(self):
        '''
            Signifies the BeamExplorer that the beam has changed
        '''
        self.beam_changed.emit((self.name,self.beam))