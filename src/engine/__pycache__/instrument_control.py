from PyQt5.QtCore import QObject, QThread, pyqtSignal,Qt
import inspect


def BuildWorker(cls):
    '''
        This function workerizes a class to allow it to be integrated into a QT Thread
    '''
    instrumentWorker=type(cls.__name__,(QObject,cls),{
        "finished":pyqtSignal(),
    })
    return instrumentWorker
     

    




if __name__ == "__main__":
    import sys
    from pathlib import Path 
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent)) #add or remove parent based on the file location
    from drivers.fakeInstruments.dumSpec import dumSpec1000
    from PyQt5.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    #spectrometer=workerize(dumSpec1000)
    specClass=BuildWorker(dumSpec1000)
    spec=specClass()
    spec.set_integration_time(0.01)
    print(spec.get_integration_time())
    thread=QThread()
    spec.moveToThread(thread)
    app = QApplication(sys.argv)
    spec.integration_time.connect(print)
    thread.start()
