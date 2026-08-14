from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time
import matplotlib.pyplot as plt


class SpectrometerPlot(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(SpectrometerPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = pg.PlotWidget()
        self.clear_button = QtWidgets.QPushButton('Clear')
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.graphWidget)
        vbox.addWidget(self.clear_button)
        widget = QtWidgets.QWidget()
        widget.setLayout(vbox)
        self.setCentralWidget(widget)
        styles = {'color':'#c8c8c8', 'font-size':'20px'}
        fontForTickValues = QtGui.QFont()
        fontForTickValues.setPixelSize(20)

        # set plot counter to clear if too many plots
        self.plotcounter = 0
        self.startplot_idx = 0

        # add firstplot for Acquire mode
        self.first_plot = True

        """ The plot starts empty. It used to be seeded with a random gaussian spanning 177 to 884 nm,
        which stayed on the plot and stretched the axes over that whole range: a real spectrum from
        the Stresing covers about 48 nm, so it was squeezed into a narrow strip and read as nothing
        being displayed. """
        self.graphWidget.getAxis('left').setStyle(tickFont = fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont = fontForTickValues)
        self.graphWidget.setLabel('left', 'Intensity (counts)', **styles)
        self.graphWidget.setLabel('bottom', 'Wavelength (nm)', **styles)
        self.graphWidget.showGrid(True,True)

        # add cross hair
        cursor = QtCore.Qt.CrossCursor
        self.graphWidget.setCursor(cursor) #set Blank Cursor
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False)
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False)
        self.graphWidget.addItem(self.crosshair_v, ignoreBounds=True)
        self.graphWidget.addItem(self.crosshair_h, ignoreBounds=True)

        # set proxy for Mouse movement
        self.proxy = pg.SignalProxy(self.graphWidget.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)

        # add value reader
        self.value_label = pg.LabelItem('Move Cursor', **{'color':'#c8c8c8', 'size':'20pt'})
        self.value_label.setParentItem(self.graphWidget.getPlotItem())
        self.value_label.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-50,10))
        self.maxvalue_label = pg.LabelItem('No Data', **{'color':'#c8c8c8', 'size':'20pt'})
        self.maxvalue_label.setParentItem(self.graphWidget.getPlotItem())
        self.maxvalue_label.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-50,35))

        # empty array
        self.y ={}
        self.wls = []

        # connect events
        self.clear_button.clicked.connect(self.clear_plot)

    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
        self.startplot_idx = self.plotcounter
        # restore crosshair
        self.graphWidget.addItem(self.crosshair_v, ignoreBounds=True)
        self.graphWidget.addItem(self.crosshair_h, ignoreBounds=True)
        self.plotcounter = 0

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, wls, spec):
        self.wls = wls
        #color = list(np.random.choice(range(256), size=3))
        self.graphWidget.plot(wls, spec, pen=QtGui.QColor.fromRgbF(plt.cm.prism(self.plotcounter)[0],plt.cm.prism(self.plotcounter)[1],
                                                                   plt.cm.prism(self.plotcounter)[2],plt.cm.prism(self.plotcounter)[3]))
        self.plotcounter = self.plotcounter + 1
        if self.plotcounter > 100:
            self.clear_plot()
            print(time.strftime('%H:%M:%S') + ' Too many spectra in live plot, clear display for performance')
            self.plotcounter = 0

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data_preview(self, wls, spec):
        if not self.first_plot:
            self.graphWidget.removeItem(self.preview_plot)
        else:
            self.first_plot = False
        self.preview_plot = self.graphWidget.plot(wls, spec, pen=pg.mkPen([200,200,200], width = 1))

    def update_crosshair(self, e):
        pos = e[0]
        """ Everything below needs mousePoint, which only exists while the pointer is over this plot.
        The label was updated unconditionally, so every mouse move outside the plot raised
        UnboundLocalError. Harmless in itself, but it floods stderr and buries real tracebacks, and
        there are now two spectrum plots, so the one that is not under the cursor raised on every
        move. """
        if not self.graphWidget.sceneBoundingRect().contains(pos):
            return
        mousePoint = self.graphWidget.getPlotItem().vb.mapSceneToView(pos)
        self.crosshair_v.setPos(mousePoint.x())
        self.crosshair_h.setPos(mousePoint.y())
        calibration_mode = False
        if calibration_mode:
            pixel = np.argmin(abs(self.wls - mousePoint.x()))
            self.value_label.setText(f"Cursor: {mousePoint.x():.1f} nm {mousePoint.y():.1f} cts {pixel:.0f} pixel")
        else:
            self.value_label.setText(f"Cursor: {mousePoint.x():.1f} nm {mousePoint.y():.1f} cts")

    @QtCore.pyqtSlot(np.ndarray)
    def update_datareader(self,max):
        self.maxvalue_label.setText(f"Data  : {max[2]:.1f} nm {max[1]:.1f} cts")




