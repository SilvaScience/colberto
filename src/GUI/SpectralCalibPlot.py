from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class SpectralCalibDataPlot(QtWidgets.QMainWindow):


    def __init__(self, graphLayoutWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
            input:
                - imageItem: (pyqtgraph.ImageItem) the image Item where the 2D data will be plotted
        '''
        super(SpectralCalibDataPlot, self).__init__(*args, **kwargs)

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
        self.plot.setLabel('bottom', 'Column index', **self.styles)
        #self.imageItem.showGrid(True, True)
        # Clear data to show plot


#    @QtCore.pyqtSlot()
#    def clear_plot(self):
#        self.graphLayoutWidget.clear()
    

    @QtCore.pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
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
            
            

class SpectralCalibFitPlot(QtWidgets.QMainWindow):


    def __init__(self, plotWidget,residual_plot_widget=None, *args, **kwargs):
        '''
            Initializes the graph to display the fitted maxima or the residual
            input:
            - plotWidget: the pyqtgraph plotwidget where the data should be plotted
            - isResidual: (bool) If true, the graph is set up to display the fit residual
        '''
        super(SpectralCalibFitPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = plotWidget
        self.residual_plot_widget=residual_plot_widget
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)
        self.ydata=None
        self.xdata=None
        self.poly=None

        # plot data: x, y values
        self.graphWidget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        if self.residual_plot_widget is not None:
            self.residual_plot_widget.setLabel('left', 'Fit residual (nm)', **self.styles)
            self.residual_plot_widget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
            self.residual_plot_widget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
            self.residual_plot_widget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
            self.residual_plot_widget.setLabel('bottom', 'Column index', **self.styles)
            self.residual_plot_widget.showGrid(True, True)
        else:
            self.graphWidget.setLabel('left', 'Wavelength (nm)', **self.styles)
        self.graphWidget.setLabel('bottom', 'Column index', **self.styles)
        self.graphWidget.showGrid(True, True)
        # Clear data to show plot
        self.clear_plot()


    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
        if self.residual_plot_widget is not None:
            self.residual_plot_widget.clear()

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

    def set_fit(self, polynomial):
        '''
            Displays the latest fit on the plot
            input:
             - polynomial: np.Polynomial object converting column indes to wavelength
        '''
        self.poly=polynomial
        self.clear_plot()
        self.set_data(self.x_array,self.y_array)
        self.graphWidget.plot(self.x_array,self.poly(self.x_array))
        self.plot_residual()

    def plot_residual(self):
        '''
            Displays the residual from the fit on the residual plot
        '''
        self.residual=np.abs(self.y_array-self.poly(self.x_array))
        self.residual_plot_widget.plot(self.x_array,self.residual)




