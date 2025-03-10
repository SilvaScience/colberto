from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class SpectralCalibDataPlot(QtWidgets.QMainWindow):


    def __init__(self, imageItem, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.ImageItem) the image Item where the 2D data will be plotted
        '''
        super(SpectralCalibDataPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.imageItem=  imageItem 
        #self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        #self.fontForTickValues = QtGui.QFont()
        #self.fontForTickValues.setPixelSize(10)
        self.ydata=None
        self.xdata=None
        self.data=None

        # plot data: x, y values
        #self.imageItem.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        #self.imageItem.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        #self.imageItem.setLabel('left', 'Wavelength', **self.styles)
        #self.imageItem.setLabel('bottom', 'Column index', **self.styles)
        #self.imageItem.showGrid(True, True)
        # Clear data to show plot
        self.clear_plot()


    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
    

    @QtCore.pyqtSlot(np.ndarray, np.ndarray,np.ndarray)
    def set_data(self, x_array, y_array,data):
        '''
            Sets up the 2D image plot and updates the display
            input:
                - x_array: (np.ndarray) 1D array holding the wavelength axis of the 2D data plot
                - y_array: (np.ndarray) 1D array holding the scanned axis of the 2D data plot
                - data: (np.ndarray) 2D array of scanned spectra
                STIL IN DEV, NOT TESTED
        '''
        self.xdata=x_array
        self.ydata=y_array
        deltax=self.xdata[1]-self.xdata[0]
        deltay=self.ydata[1]-self.ydata[0]
        if self.data is None:
            self.tr=QtGui.QTransform()
        else:
            self.imageItem.setImage(data)
        #self.tr.scale(deltax,deltay)
        #self.img.setTransform(self.tr)
        #tr.translate() Might be necessary to make the axes right
        
        self.data=data
        self.graphWidget.clear()
            
            







