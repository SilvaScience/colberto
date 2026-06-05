from PyQt5 import QtCore
import time
from collections import defaultdict
import pyvisa
import requests
import json


class CryoPasqal(QtCore.QThread):
    # 1. Variables de classe OBLIGATOIRES pour l'arbre du GUI
    name = 'CryoPasqal'
    type = 'Cryostat'

    def __init__(self, port_com='ASRL9::INSTR'):
        super(CryoPasqal, self).__init__()
        
        self.parameter_dict = defaultdict()
        self.parameter_dict['Set_T'] = 5
        self.parameter_dict['OnOff_comp'] = 0
        self.parameter_dict['OnOff_Loop'] = 0
        self.parameter_dict['ChannelA_T'] = 300
        self.parameter_dict['ChannelB_T'] = 300
        self.parameter_dict['ChannelC_T'] = 300
        self.parameter_dict['ChannelD_T'] = 300
        self.parameter_dict['MainController_T'] = 300

        
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['Set_T']['val'] = 5
        self.parameter_display_dict['Set_T']['unit'] = ' K'
        self.parameter_display_dict['Set_T']['max'] = 1000
        self.parameter_display_dict['Set_T']['read'] = False

        self.parameter_display_dict['OnOff_comp']['val'] = 0
        self.parameter_display_dict['OnOff_comp']['unit'] = ' '
        self.parameter_display_dict['OnOff_comp']['max'] = 1
        self.parameter_display_dict['OnOff_comp']['read'] = False


        self.parameter_display_dict['OnOff_Loop']['val'] = 0
        self.parameter_display_dict['OnOff_Loop']['unit'] = ' '
        self.parameter_display_dict['OnOff_Loop']['max'] = 1
        self.parameter_display_dict['OnOff_Loop']['read'] = False

        self.parameter_display_dict['ChannelA_T']['val'] = 300
        self.parameter_display_dict['ChannelA_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelA_T']['max'] = 1000
        self.parameter_display_dict['ChannelA_T']['read'] = True

        self.parameter_display_dict['ChannelB_T']['val'] = 300
        self.parameter_display_dict['ChannelB_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelB_T']['max'] = 1000
        self.parameter_display_dict['ChannelB_T']['read'] = True

        self.parameter_display_dict['ChannelC_T']['val'] = 300
        self.parameter_display_dict['ChannelC_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelC_T']['max'] = 1000
        self.parameter_display_dict['ChannelC_T']['read'] = True

        self.parameter_display_dict['ChannelD_T']['val'] = 300
        self.parameter_display_dict['ChannelD_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelD_T']['max'] = 1000
        self.parameter_display_dict['ChannelD_T']['read'] = True

        self.parameter_display_dict['MainController_T']['val'] = 300
        self.parameter_display_dict['MainController_T']['unit'] = ' K'
        self.parameter_display_dict['MainController_T']['max'] = 1000
        self.parameter_display_dict['MainController_T']['read'] = True


        # defining waitTime
        self.waitTime = 0.1

        # start updating temp
        self.UpdateWorker = UpdateWorker()
        self.UpdateWorker.new_T.connect(self.update_temp)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        if parameter == 'set_T':
            self.update_set_T(value)
            self.UpdateWorker.target = value


        # ... (Initialise pyvisa ici avec ton try/except comme on a vu précédemment) ...

    # --- 3. Fonction OBLIGATOIRE appelée par le GUI pour le contrôle ---
    def set_parameter(self, param, value):
        """Cette fonction est déclenchée quand tu tapes une valeur dans le GUI"""
        if param == 'Set_T':
            # Code VISA pour envoyer la consigne de température au cryostat
            # Exemple : self.Opti.write(f'set_temp {value}')
            self.parameter_dict['Set_T'] = value
            print(f"La consigne de température a été changée à {value} K")
            
        elif param == 'OnOff_comp':
            # Code VISA pour allumer/éteindre le compresseur
            pass

    # --- 4. Mise à jour des valeurs lues pour l'affichage ---
    def update_temp(self, temps_list):
        """Connecté au signal de ton UpdateWorker"""
        # Met à jour le dictionnaire que main.py lit continuellement
        self.parameter_dict['ChannelA_T'] = temps_list[3] # Index selon ton format

    def set_temperature(self, target_temp):
        if getattr(self, 'is_connected', False) is False:
            print("Error, Impossible to change the temperature, Cryostat is not connected.")

        try:
            Commande = f'SOUR:TEMP {target_temp} K'
            self.Opti.write(Commande)
            print(f"Consigne envoyée au cryostat : {target_temp} K")

            self.parameter_dict['Set_T'] = target_temp
        except Exception as e:
            print(f"Erreur de communication VISA lors du changement de température : {e}") 

class UpdateWorker(QtCore.QThread):
    new_T = QtCore.pyqtSignal(float)

    def __init__(self):
        super(UpdateWorker, self).__init__()
        self.currentT = []
        self.stop = False
        self.waitTime = 0.1
        self.target = 300

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.read_T()

            # waiting to remeasure the temperature
            time.sleep(self.waitTime)
            self.new_T.emit(self.readtemp)

    def read_T(self):
        # read the current platform target temperature
        resp = requests.get('http://10.131.3.6:47101/v1/sampleChamber/temperatureControllers/platform/thermometer/properties/sample')
        # target = self.target + np.random.rand(1)
        return resp.json()['sample']['temperature']        

    def set_T(self,Temp):
        requests


