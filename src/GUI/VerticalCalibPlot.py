from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class VerticalCalibPlot(QtWidgets.QMainWindow):


    def __init__(self, plotWidget, *args, **kwargs):
        '''
            Initializes the graph to diplay the vertical calibration data.
        '''
        super(VerticalCalibPlot, self).__init__(*args, **kwargs)

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
        self.graphWidget.setLabel('bottom', 'Row index', **self.styles)
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
        '''
        self.xdata=x_array
        self.ydata=y_array
        self.graphWidget.clear()
        self.graphWidget.plot(x_array,y_array)

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def draw_regions(self,regions):
        '''
            Draws regions associated to labels on the plot
            input:
                - regions (dict): dict of np.1darray (2 elements [top_limit, bottom_limit]) with keys as labels
        '''
        if self.xdata is not None:
            self.set_data(self.xdata,self.ydata)
        else:
            self.clear_plot()
        yRange=self.graphWidget.getAxis('left').range
        for region in regions:
            lower_bound=regions[region][0]
            upper_bound=regions[region][1]
            if lower_bound is not None:
                self.graphWidget.plot([lower_bound, lower_bound],yRange,symbolPen=pg.mkPen('r'))
                text=pg.TextItem(region+'->',color='r',anchor=(0,0))
                self.graphWidget.addItem(text)
                text.setPos(lower_bound,yRange[1])
            if upper_bound is not None:
                self.graphWidget.plot([upper_bound, upper_bound],yRange,symbolPen=pg.mkPen('r'))
                text=pg.TextItem('<-'+region,color='r',anchor=(1,1))
                self.graphWidget.addItem(text)
                text.setPos(upper_bound,yRange[0])
        self.regions=regions


            
            







