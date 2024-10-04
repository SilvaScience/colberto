from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
import databroker
from bluesky.utils import ProgressBarManager
from ophyd.sim import det1, det2  # two simulated detectors
from ophyd.sim import det,motor
from bluesky.plans import count,scan

def setup_bluesky():
    '''
    Initial configuration of BlueSky engine and requirements
    '''
    if not found_catalogs():
        string_paths=''
        for path in list(databroker.catalog_search_path()):
            string_paths+='\n %s'%str(path)
        raise RuntimeError('No Databroker catalog was found. Make sure a catalog configuration file is present in %s'%string_paths)

def found_catalogs():
    '''
    Checks if Databroker catalogs exist on the machine
    see https://blueskyproject.io/databroker/how-to/file-backed-catalog.html

    returns True if catalogs are found locally 
    '''
    if list(databroker.catalog)==[]:
        return False
    else:
        return True

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
