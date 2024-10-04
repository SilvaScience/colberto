from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from databroker import temp
from bluesky.utils import ProgressBarManager
from ophyd.sim import det1, det2  # two simulated detectors
from ophyd.sim import det,motor
from bluesky.plans import count,scan

class Runtime():
    def __init__(self):
        '''
        Instantiates the BlueSky runtime and configures it.
        '''
        self.RE=RunEngine({})
        self.setup_catalog()

    def setup_catalog(self):
        '''
        Initial configuration of databroker
        '''
        catalog=temp()
        self.RE.subscribe(catalog.v1.insert)
        


#RE=RunEngine({})
#bec = BestEffortCallback()
## Send all metadata/data captured to the BestEffortCallback.
#RE.subscribe(bec)
#catalog=db.catalog['bluesky_tutorial']
## Insert all metadata/data captured into db.
#RE.subscribe(catalog.insert)
#RE.waiting_hook = ProgressBarManager()
#
#dets = [det1, det2]   # a list of any number of detectors
#
#RE(count(dets,num=5))
#
#
#RE(scan([det],motor,-1,1,10))
