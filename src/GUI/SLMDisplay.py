from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time

class SLMDisplay(QtWidgets.QMainWindow):


    def __init__(self, graphLayoutWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.GraphicsLayoutWidget) the image Item where the 2D data will be plotted
        '''
        super(SLMDisplay, self).__init__(*args, **kwargs)

        self.graphLayoutWidget=graphLayoutWidget 
        self.graphLayoutWidget.show()
        self.plot=self.graphLayoutWidget.addPlot()
        self.data=None
        self.image=pg.ImageItem(axisOrder='row-major')
        self.plot.showAxes(False)  # frame it with a full set of axes
        self.plot.invertY(True)
        self.plot.addItem(self.image)
    @QtCore.pyqtSlot(np.ndarray)
    def set_data(self,data):
        '''
            Sets up the 2D image plot and updates the display
            input:
                - data: (np.ndarray) 2D array of scanned spectra
        '''
        self.data=data
        self.image.setImage(data)
            