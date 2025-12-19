from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class DelayCalibrationPlot(QtWidgets.QMainWindow):


    def __init__(self, graphLayoutWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.ImageItem) the image Item where the 2D data will be plotted
        '''
        super(DelayCalibrationPlot, self).__init__(*args, **kwargs)

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
        self.plot.setLabel('left', 'Wavelength [nm]', **self.styles)
        self.plot.setLabel('bottom', 'Delay [fs]', **self.styles)
        #self.imageItem.showGrid(True, True)
        # Clear data to show plot


#    @QtCore.pyqtSlot()
#    def clear_plot(self):
#        self.graphLayoutWidget.clear()
    

    @QtCore.pyqtSlot(np.ndarray, np.ndarray,np.ndarray)
    def set_data(self, x_array, y_array, data):
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
            self.rect = QtCore.QRectF(x_array[0]-deltax/2, y_array[0]-deltay/2, x_array[-1]-x_array[0], y_array[-1]-y_array[0])
            self.ydata=y_array
            self.data=data
            self.xdata=x_array
            self.image.setImage(data)
            self.image.setRect(self.rect)
        else:
            self.xdata=None
            self.ydata=None
            self.data=None

class DelaySelectionPlot(QtWidgets.QMainWindow):

    def __init__(self, graphLayoutWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.ImageItem) the image Item where the 2D data will be plotted
        '''
        super(DelaySelectionPlot, self).__init__(*args, **kwargs)

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
        self.plot.setLabel('left', 'Wavelength [nm]', **self.styles)
        self.plot.setLabel('bottom', 'Chirp [fs²/rad²]', **self.styles)

    @QtCore.pyqtSlot(np.ndarray, np.ndarray,np.ndarray)
    def set_data(self, x_array, y_array, data):
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
            self.rect = QtCore.QRectF(x_array[0]-deltax/2, y_array[0]-deltay/2, x_array[-1]-x_array[0], y_array[-1]-y_array[0])
            self.ydata=y_array
            self.data=data
            self.xdata=x_array
            self.image.setImage(data)
            self.image.setRect(self.rect)
        else:
            self.xdata=None
            self.ydata=None
            self.data=None

class DelayFitPlot(QtWidgets.QMainWindow):

    def __init__(self, plotWidget, *args, **kwargs):
        '''
            Initializes the graph to display the fitted maxima or the residual
            input:
            - plotWidget: the pyqtgraph plotwidget where the data should be plotted
            - isResidual: (bool) If true, the graph is set up to display the fit residual
        '''
        super(DelayFitPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = plotWidget
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)
        self.ydata=None
        self.xdata=None
        self.poly=None

        # plot data: x, y values
        self.graphWidget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.setLabel('left', 'Norm. int.', **self.styles)
        self.graphWidget.setLabel('bottom', 'Delay [fs]', **self.styles)
        self.graphWidget.showGrid(True, True)
        # Clear data to show plot
        self.clear_plot()

    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, x_array, y_array):
        '''
            Updates the data in the plot
            input:
             - x_array: np.1darray the x-axis of the data
             - y_array: np.1darray the y-axis of the data

        '''
        self.x_array=x_array
        self.y_array=y_array
        self.graphWidget.clear()
        self.graphWidget.plot(x_array,y_array,symbol='o')

    def set_fit(self, x_array, y_array_fit, mu, sigma):
        '''
            Displays the latest fit on the plot
            input:
             - polynomial: np.Polynomial object converting column index to wavelength
        '''
        self.y_array_fit = y_array_fit
        self.set_data(self.x_array, self.y_array)
        self.graphWidget.plot(self.x_array, self.y_array_fit)

        FWHM = 2 * np.sqrt(2 * np.log(2)) * sigma   # sigma from Gaussian fit

        text = pg.TextItem(
            f"μ = {mu:.3f} fs\nFWHM = {FWHM:.3f} fs",
            anchor=(0, 0.5),
            color='w'
        )
        self.graphWidget.addItem(text)

        # Position the text vertically centered on the left
        vb = self.graphWidget.getPlotItem().getViewBox()
        (x_min, x_max), (y_min, y_max) = vb.viewRange()

        text.setPos(x_min, (y_min + y_max) / 2)