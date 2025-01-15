from PySide6.QtCore import QObject, QThread, Signal
import numpy as np

class DataWorker(QObject):
    '''
        Class that instanstiate a worker to run the provided function in a parrallel thread.
        Designed for a data acquisition function that return a single np array object
    '''
    finished = Signal()
    data = Signal(np.ndarray)
    def __init__(self,function_to_run):
        '''
            Creates an instances of the DataWorker with the inherited attributes of a QObject
            input:
             function_to_run: a function that takes no arguments and returns a single np.ndarray
            returns:
                A DataWorker object 
        '''
        super().__init__()
        self.function_to_run=function_to_run

    def run(self):
        '''
            The function that will be run when a QThread is started if connected to the thread.started signal.
        '''
        output = self.function_to_run()
        if not output is None:
            self.data.emit(output)
        self.finished.emit()

def run_threaded_task(function_to_run):
    '''
        Runs the provided function in a parrallel thread and returns the thread and the worker running the function
        input:
            function_to_run: a function that takes no arguments and returns a single np.ndarray
        output:
            worker: the worker running the provided function
            thread: The Qthread in which the worker is running the task

    '''
    # Step 2: Create a QThread object
    thread = QThread()
    # Step 3: Create a worker object
    worker = DataWorker(function_to_run)
    # Step 4: Move worker to the thread
    worker.moveToThread(thread)
    # Step 5: Connect signals and slots
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    # Step 6: Start the thread
    thread.start()
    return worker,thread