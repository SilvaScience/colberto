from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class ChirpCalibrationPlot(QtWidgets.QMainWindow):


    def __init__(self, graphLayoutWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.ImageItem) the image Item where the 2D data will be plotted
        '''
        super(ChirpCalibrationPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphLayoutWidget= graphLayoutWidget 
        self.graphLayoutWidget.show()
        self.plot=self.graphLayoutWidget.addPlot()
        leftAxis = self.plot.getAxis('left')
        bottomAxis = self.plot.getAxis('bottom')
        font = QtGui.QFont("Roboto", 12)
        leftAxis.setTickFont(font)
        bottomAxis.setTickFont(font)
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)
        self.ydata=None
        self.xdata=None
        self.data=None
        self.tr=QtGui.QTransform()
        self.image=pg.ImageItem()
        self.plot.addItem(self.image)
        # plot data: x, y values
        self.plot.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.plot.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.plot.setLabel('left', 'Wavelength', **self.styles)
        self.plot.setLabel('bottom', 'Chirp', **self.styles)
        #self.imageItem.showGrid(True, True)
        # Clear data to show plot


#    @QtCore.pyqtSlot()
#    def clear_plot(self):
#        self.graphLayoutWidget.clear()
    

    @QtCore.pyqtSlot(np.ndarray, np.ndarray,np.ndarray)
    def set_data(self, x_array, y_array,data):
        '''
            Sets up the 2D image plot and updates the display
            input:
                - x_array: (np.ndarray) 1D array holding the wavelength axis of the 2D data plot
                - y_array: (np.ndarray) 1D array holding the scanned axis of the 2D data plot
                - data: (np.ndarray) 2D array of scanned spectra
        '''
        
        if np.shape(data)[0]>=2 and np.shape(data)[1]>=2: # Don't plot it if it is not a 2D array 
            
            deltax=x_array[1]-x_array[0]
            self.deltax=deltax
            deltay=y_array[1]-y_array[0]
            self.deltay=deltay
            self.rect = QtCore.QRectF(x_array[0]-deltax/2,y_array[0]-deltay/2,x_array[-1]-x_array[0],y_array[-1]-y_array[0])
            self.ydata=y_array
            self.data=data
            self.xdata=x_array
            self.image.setImage(data)
            self.image.setRect(self.rect)
        else:
            self.xdata=None
            self.ydata=None
            self.data=None