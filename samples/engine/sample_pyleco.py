from pyleco.coordinators.coordinator import Coordinator 
from pyleco.coordinators.proxy_server import start_proxy
from pyleco.management.starter import Starter
from pyleco.directors.starter_director import StarterDirector
from pyleco.directors.transparent_director import TransparentDirector

testCoordinator=Coordinator()
start_proxy()
starter=Starter(name="starter",directory="/home/thouin/Documents/Repo/colberto/samples/engine/demoStarterFolder")
starter.listen()
#director=StarterDirector(actor="starter")
#director.start_tasks(["dumSpec1000_controller"])

#specDirector=TransparentDirector(actor="spectrometer")

#print(specDirector.device.get_integration_time())