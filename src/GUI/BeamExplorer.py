from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QTableWidget,QSpinBox,QCheckBox, QTableWidgetItem, QLineEdit
from PyQt5 import QtCore,uic
import sys
import os
import logging
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial as P
import pyqtgraph as pg

logger = logging.getLogger(__name__)
class BeamExplorer(QWidget):
    """
        Display the properties of the beams currently held in the provided DataHandler
    """
    request_beams= QtCore.pyqtSignal()
    phase_image=QtCore.pyqtSignal(np.ndarray)
    beams_changed=QtCore.pyqtSignal(object)
    
    def __init__(self,beamDict):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setWindowTitle("Beam explorer")
        self.beamWidgets=[]
        self.apply_pushbutton=QPushButton("&APPLY BEAMS",parent=self)
        self.apply_pushbutton.clicked.connect(self.update_beamDict_and_show)
        self.layout.addWidget(self.apply_pushbutton)
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
        
    def update_beamDict_and_show(self):
        """
            Updates all beams when updated from BeamWidgets and emits the phase image associated to all the beams
            input:
                - beam_key_value: tuple (str, Beam) consisting of beam's name and the beam itself
        """
        for beamWidget in self.beamWidgets:
            beam_key_value=beamWidget.update_beam()
            self.beamDict[beam_key_value[0]]=beam_key_value[1]
        self.beams_changed.emit(self.beamDict)
        image=None
        for beam in self.beamDict.values():
            if image is None:
                image=beam.makeGrating()
            #else:
            #    image=image+beam.makeGrating()
        self.phase_image.emit(image)
        

    @QtCore.pyqtSlot()
    def stop(self):
        return



class BeamWidget(QWidget):
    """
        Instantiate the Widget displaying a single beam's properties. 
    """

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
        self.mask_pushbutton=self.findChild(QPushButton,'mask_pushbutton')
        self.beam_label=self.findChild(QLabel,'beam_label')
        self.grating_period=self.findChild(QSpinBox,'grating_period_value')
        self.lambda_comp=self.findChild(QLineEdit,'lambda_comp_box')
        self.lambda_delay=self.findChild(QLineEdit,'lambda_delay_box')
        self.grating_amplitude=self.findChild(QLineEdit,'grating_amplitude_lineedit')
        self.delimiter_table=self.findChild(QTableWidget,'delimiter_table_widget')
        self.phase_coeff_table=self.findChild(QTableWidget,'phase_coeff_table')
        self.relative_checkbox=self.findChild(QCheckBox,'relative_checkbox')
        self.graphlayout=self.findChild(pg.PlotWidget,'beam_plot')
        self.styles = {'color':'#c8c8c8', 'font-size':'10px'}
        self.graphlayout.setLabel('bottom', 'Wavelength (nm)', **self.styles)
        self.graphlayout.setLabel('left', 'Phase (pi)', **self.styles)
        # connect events
        self.mask_pushbutton.clicked.connect(self.toggle_beam_on_off_display)
        self.import_beam(name,beam)

    def toggle_beam_on_off_display(self):
        """
            Flips the status of the Mask PushButton when triggered
        """
        if self.mask_pushbutton.text()=='BEAM OFF':
            self.mask_pushbutton.setText('BEAM ON')
        elif self.mask_pushbutton.text()=='BEAM ON':
            self.mask_pushbutton.setText('BEAM OFF')

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
        self.grating_amplitude.setText(str(self.beam.get_gratingAmplitude()))
        self.lambda_comp.setText(str(self.beam.get_compressionCarrier(unit='wavelength')))
        self.lambda_delay.setText(str(self.beam.get_delayCarrier(unit='wavelength')))
        if self.beam.get_beamStatus():
            self.mask_pushbutton.setText('BEAM ON')
        else:
            self.mask_pushbutton.setText('BEAM OFF')
        if self.beam.get_current_phase_mode()=='relative':
            self.relative_checkbox.setChecked(True)
        else:
            self.relative_checkbox.setChecked(False)
        [self.delimiter_table.setItem(0,i,QTableWidgetItem(str(value))) for i,value in enumerate(self.beam.get_beamVerticalDelimiters())]
        [self.delimiter_table.setItem(1,i,QTableWidgetItem(str(value))) for i,value in enumerate(self.beam.get_beamHorizontalDelimiters())]
        [self.phase_coeff_table.setItem(0,i,QTableWidgetItem('%d'%coeff)) for i,coeff in enumerate(self.beam.get_optimalPhase(units_to_return='fs').coef)]
        [self.phase_coeff_table.setItem(1,i,QTableWidgetItem('%d'%coeff)) for i,coeff in enumerate(self.beam.get_currentPhase(units_to_return='fs',for_display=True).coef)]
        self.plot_phase()
        #[self.phase_coeff_table.item(1,i).setText(coeff) for i,coeff in enumerate(self.beam.get_currentPhase(mode=mode).coeff)]
    def plot_phase(self):
        '''
            Plots the current phase of the beam either relative to the compression or absolute
        '''
        self.graphlayout.clear()
        self.graphlayout.plot(self.beam.get_spectrumAtPixel(),1./np.pi*self.beam.get_sampledCurrentPhase(mode=self.beam.get_current_phase_mode()))

    def toggle_beam_to_slm(self):
        '''
           Toggle wether the current settings of the beam are sent to the SLM. 
        '''

    def update_beam(self):
        '''
            Updates the beams from the parameters displayed in the widget and returns the beam 
            input: None
            output:
                - tuple consisting of beam name and the Beam object
        '''
        self.beam.set_gratingPeriod(self.grating_period.value())
        self.beam.set_gratingAmplitude(float(self.grating_amplitude.text()))
        self.beam.set_compressionCarrierWave(float(self.lambda_comp.text()))
        self.beam.set_delayCarrierWave(float(self.lambda_delay.text()))
        if self.mask_pushbutton.text()=='BEAM OFF':
            self.beam.set_beamStatus(False)
        else:
            self.beam.set_beamStatus(True)
        if self.relative_checkbox.isChecked():
            self.beam.set_current_phase_mode('relative')
        else:
            self.beam.set_current_phase_mode('absolute')
        self.beam.set_beamVerticalDelimiters([int(self.delimiter_table.item(0,0).text()),int(self.delimiter_table.item(0,1).text())])
        self.beam.set_beamHorizontalDelimiters([int(self.delimiter_table.item(1,0).text()),int(self.delimiter_table.item(1,1).text())])
        self.beam.set_optimalPhase(P([float(self.phase_coeff_table.item(0,i).text()) for i in range(self.phase_coeff_table.columnCount()) if self.phase_coeff_table.item(0,i) is not None]))
        self.beam.set_currentPhase(P([float(self.phase_coeff_table.item(1,i).text()) for i in range(self.phase_coeff_table.columnCount()) if self.phase_coeff_table.item(1,i) is not None]))

        return self.name,self.beam

    @QtCore.pyqtSlot()
    def stop(self):
        return