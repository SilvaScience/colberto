# -*- coding: utf-8 -*-
"""
Created on Wed Mar  5 12:53:08 2025

@author: simon
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class Chirp_calibration_plot(QtWidgets.QMainWindow):


    def __init__(self, plotWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the chirp calibration data.
        '''
        super(Chirp_calibration_plot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = plotWidget
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(10)


        # plot data: x, y values
        self.graphWidget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.setLabel('left', 'Wavelength (nm)', **self.styles)
        self.graphWidget.setLabel('bottom', 'GVD', **self.styles)
        self.graphWidget.showGrid(True, True)
        # Clear data to show plot
        self.clear_plot()


    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, x_array, y_array):
        self.graphWidget.clear()
        self.graphWidget.plot(x_array,y_array)
