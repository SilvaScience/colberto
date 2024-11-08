"""Example scheme for an Actor for a dummy spectrometer. 'dumSpec'"""

from pyleco.actors.actor import Actor
from dumSpec import dumSpec1000

# Parameters
intTime= 20e-3# Some parameter the device could need on startup

def task(stop_event) -> None:
    """The task which is run by the starter."""
    with Actor(
        name="spectrometer",  # you can access it under this name
        device_class=dumSpec1000,  # the class to instantiate later on
    ) as actor:
        actor.connect(intTime)  # create an instance `actor.device = dumSpec1000(intTime)`

        actor.listen(stop_event=stop_event)  # listen for commands