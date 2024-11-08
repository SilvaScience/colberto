from pyleco.directors.starter_director import StarterDirector
from matplotlib import pyplot as plt
from pyleco.directors.transparent_director import TransparentDirector
# First start the servers by running in separate terminal windows the coordinator, proxy_server and starter files like
# Example of these on my machine
#  python3 /home/thouin/miniconda3/envs/colberto_pyleco/lib/python3.13/site-packages/pyleco/coordinators/coordinator.py
#  python3 /home/thouin/miniconda3/envs/colberto_pyleco/lib/python3.13/site-packages/pyleco/coordinators/proxy_server.py
#  python3 /home/thouin/miniconda3/envs/colberto_pyleco/lib/python3.13/site-packages/pyleco/management/starter.py --directory /home/thouin/Documents/Repo/colberto/samples/engine/demoStarterFolde


try:
    director=StarterDirector(actor="starter")
    director.start_tasks(["dumSpec1000_controller"])
except Exception:
    print(Exception)

try:
    specDirector=TransparentDirector(actor="spectrometer")
except Exception:
    print(Exception)
print(specDirector.call_action(action="get_integration_time"))
specDirector.call_action(action="set_integration_time",t=0.1)
print(specDirector.call_action(action="get_integration_time"))
# This part below doesn't work because I am probably abusing the controller and should instead use a data publisher.
#wave,spec=specDirector.call_action(action="get_spectrum")
#plt.figure()
#plt.plot(wave,spec)
#plt.show()