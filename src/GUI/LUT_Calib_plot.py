from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time

class LUT_Calib_plot(QtWidgets.QMainWindow):

    def __init__(self, plotWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the spectra taken during a LUT calibration.
        '''
        super(LUT_Calib_plot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = plotWidget
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)
        self.ydata=None
        self.xdata=None
        self.regions=None

        # plot data: x, y values
        self.graphWidget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.setLabel('left', 'Intensity', **self.styles)
        self.graphWidget.setLabel('bottom', 'Wavelength (nm)', **self.styles)
        self.graphWidget.showGrid(True, True)
        # Clear data to show plot
        self.clear_plot()


    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, x_array, y_array):
        self.xdata=x_array
        self.ydata=y_array
        self.graphWidget.clear()
        self.graphWidget.plot(x_array,y_array)

class LUT_Calib_intensity_plot(QtWidgets.QMainWindow):

    def __init__(self, plotWidget, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.graphWidget = plotWidget

        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}

        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)

        self.plot_items = []
        self.lines = []

        self.graphWidget.getAxis('left').setStyle(
            tickFont=self.fontForTickValues
        )

        self.graphWidget.getAxis('bottom').setStyle(
            tickFont=self.fontForTickValues
        )

        self.graphWidget.setLabel(
            'left',
            'Normalized intensity',
            **self.styles
        )

        self.graphWidget.setLabel(
            'bottom',
            'Grayscale',
            **self.styles
        )

        self.graphWidget.showGrid(True, True)


    @QtCore.pyqtSlot()
    def clear_all(self):

        self.graphWidget.clear()

        self.plot_items = []
        self.lines = []


    @QtCore.pyqtSlot()
    def clear_lines(self):

        for line in self.lines:
            self.graphWidget.removeItem(line)

        self.lines = []


    @QtCore.pyqtSlot()
    def clear_data(self):

        for item in self.plot_items:
            self.graphWidget.removeItem(item)

        self.plot_items = []


    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def add_data(self, x_array, y_array):

        curve = self.graphWidget.plot(x_array, y_array)

        self.plot_items.append(curve)


    @QtCore.pyqtSlot(int)
    def draw_line(self, grayscale):

        line = pg.InfiniteLine(
            pos=grayscale,
            angle=90,
            pen=pg.mkPen('r', width=2)
        )

        self.graphWidget.addItem(line)

        self.lines.append(line)