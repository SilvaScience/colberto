from PyQt5 import QtWidgets, uic, QtCore
import os

class CryostatTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Chargement de l'interface graphique dessinée dans Designer
        current_dir = os.path.dirname(__file__)
        ui_path = os.path.join(current_dir, 'cryostattab.ui') 
        uic.loadUi(ui_path, self)
        
        # Référence vers le driver (sera injectée par main.py ou Instruments.py)
        self.driver = None

    def set_driver(self, driver_instance):
        """Permet d'associer le driver matériel à cette interface graphique"""
        self.driver = driver_instance
        
        # 2. Connexion du signal du Worker pour mettre à jour l'affichage en temps réel
        if hasattr(self.driver, 'UpdateWorker'):
            self.driver.UpdateWorker.new_T.connect(self.refresh_interface_display)
            
        # 3. Connexions des Éléments Interactifs (Boutons et Actions)
        self.btn_apply_temp.clicked.connect(self.action_apply_thermal_settings)
        self.btn_compressor.clicked.connect(self.action_toggle_compressor)
        self.btn_reset_alarm.clicked.connect(self.action_reset_alarm)

    # =========================================================================
    # ENVOI DES COMMANDES (GUI -> DRIVER)
    # =========================================================================

    def action_apply_thermal_settings(self):
        """Récupère les entrées de l'interface et les envoie au driver"""
        if not self.driver: return
        
        # Déterminer la boucle active (Boucle 1 ou Boucle 2) selon la ComboBox
        # index 0 -> Boucle 1, index 1 -> Boucle 2
        loop = self.comboBox_loop_state.currentIndex() + 1
        
        # A. Envoi de la consigne de température (Setpoint)
        target_temp = self.spinBox_setpoint.value()
        self.driver.set_temperature_setpoint(loop, target_temp)
        
        # B. Envoi du Heater Range (Off=0, Low=1, Medium=2, High=3)
        # index 0='off', 1='Low', 2='Medium', 3='High' dans ton comboBox
        heater_range = self.comboBox.currentIndex()
        self.driver.set_heater_range(loop, heater_range)
        
        # C. Envoi des gains PID
        p = self.SpinBox_P.value()
        i = self.spinBox_I.value()
        d = self.spinBox_D.value()
        self.driver.set_pid_parameters(loop, p, i, d)

    def action_toggle_compressor(self):
        """Déclenché par le bouton 'Push to start' du compresseur"""
        if not self.driver: return
        # Puisque le bouton est 'checkable', isChecked() renvoie True s'il est enfoncé
        is_on = self.btn_compressor.isChecked()
        self.driver.set_compressor_state(is_on)

    def action_reset_alarm(self):
        """Déclenché par le bouton 'Reset Alarm'"""
        if not self.driver: return
        self.driver.reset_compressor_alarm()

    # =========================================================================
    # REFRESH DE L'AFFICHAGE (DRIVER WORKER -> GUI)
    # =========================================================================

    def refresh_interface_display(self, data_list):
        """Méthode exécutée en arrière-plan à chaque seconde pour rafraîchir l'écran"""
        # Sécurité : On s'assure que le dictionnaire du driver est accessible
        if not self.driver or not hasattr(self.driver, 'parameter_dict'): return
        
        params = self.driver.parameter_dict

        # 1. Mise à jour des températures (Canaux A à E)
        self.label_temp_A.setText(f"{params.get('ChannelA_T', 300.0):.2f} K")
        self.label_temp_B.setText(f"{params.get('ChannelB_T', 300.0):.2f} K")
        self.label_temp_C.setText(f"{params.get('ChannelC_T', 300.0):.2f} K")
        self.label_temp_D.setText(f"{params.get('ChannelD_T', 300.0):.2f} K")
        self.label_temp_E.setText(f"{params.get('ChannelE_T', 300.0):.2f} K")

        # 2. Mise à jour des pressions (Canaux F et G)
        # Convertit la valeur (ex: Pa) ou affiche brute selon la jauge
        self.label_pressure_F.setText(f"{params.get('PressureF', 101300.0):.1f} Pa")
        self.label_pressure_G.setText(f"{params.get('PressureG', 101300.0):.1f} Pa")

        # 3. Synchronisation de l'état graphique du compresseur (Bouton et Voyant)
        comp_on = params.get('OnOff_comp', 0) == 1
        
        # Ajuster le bouton pour qu'il reste enfoncé/relâché en accord avec la machine
        self.btn_compressor.setChecked(comp_on)
        self.btn_compressor.setText("Stop Compres." if comp_on else "Push to start")
        
        # Ajuster le label indicateur "On / Off" à côté du bouton
        if comp_on:
            self.label_22.setText("On")
            self.label_22.setStyleSheet("background-color: green; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")
        else:
            self.label_22.setText("Off")
            self.label_22.setStyleSheet("background-color: gray; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")

        # 4. Mise à jour des statuts de sécurité (Stabilité et Alarme)
        stability = params.get('Stability', 'En cours')
        self.label_statut_settle.setText(stability)
        if stability == "Stable":
            self.label_statut_settle.setStyleSheet("background-color: green; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")
        else:
            self.label_statut_settle.setStyleSheet("background-color: orange; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")

        critical_state = params.get('Critical_State', 'OK')
        self.label_statut_alarm.setText(critical_state)
        if critical_state == "OK":
            self.label_statut_alarm.setStyleSheet("background-color: green; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")
        else:
            self.label_statut_alarm.setStyleSheet("background-color: red; color: white; font-weight: bold; border-radius: 4px; padding: 2px;")