import sys
from time import sleep
#import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
from src.drivers.fakeInstruments.dumSpec import dumSpec1000
from src.engine.threading import run_threaded_task
from PySide6.QtCore import QObject, QThread,Qt
import pyqtgraph as pg
import numpy as np
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

class Window(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clicksCount = 0
        self.signal_plotted=np.array([])
        self.xaxis_plotted=np.array([])
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("Demo of a spectrometer acquisition")
        self.resize(300, 150)
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        # Create and connect widgets
        self.clicksLabel = QLabel("Counting: 0 clicks", self)
        self.clicksLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.stepLabel = QLabel("Long-Running Step: 0")
        self.stepLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.countBtn = QPushButton("Click me!", self)
        self.countBtn.clicked.connect(self.countClicks)
        self.longRunningBtn = QPushButton("Acquire spectrum!", self)
        self.longRunningBtn.clicked.connect(self.runLongTask)
        # set the plotting
        self.plot_graph=pg.PlotWidget(labels={'left':'ADU Counts', 'bottom':'Wavelength (nm)'})
        self.current_curve=self.plot_graph.plot([])
        # Set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.clicksLabel)
        layout.addWidget(self.countBtn)
        layout.addStretch()
        layout.addWidget(self.plot_graph)
        layout.addWidget(self.stepLabel)
        layout.addWidget(self.longRunningBtn)
        self.centralWidget.setLayout(layout)
        #Set up fake instrument
        self.spec=dumSpec1000()
        self.spec.set_integration_time(2)
        self.xaxis_plotted=self.spec.get_wave()
        self.current_curve.setData(self.xaxis_plotted,np.zeros(self.xaxis_plotted.shape))

    def countClicks(self):
        self.clicksCount += 1
        self.clicksLabel.setText(f"Counting: {self.clicksCount} clicks")

    def plot_data(self,data):
        self.spectrum_plotted=data
        self.current_curve.setData(self.xaxis_plotted,self.spectrum_plotted)
        
    def runLongTask(self):
        '''
            This interfaces between the data acquisition and the GUI
        '''
        self.stepLabel.setText("Acquiring spectrum!!!")
        self.worker,self.thread=run_threaded_task(self.spec.get_spectrum)
        self.worker.data.connect(self.plot_data)
        
        self.longRunningBtn.setEnabled(False)
        
        self.thread.finished.connect(
            lambda: self.longRunningBtn.setEnabled(True)
        )
        self.thread.finished.connect(
            lambda: self.stepLabel.setText("Waiting for user interaction")
        )

app = QApplication(sys.argv)
win = Window()
win.show()
sys.exit(app.exec())