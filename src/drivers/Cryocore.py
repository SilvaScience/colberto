# -*- coding: utf-8 -*-
"""
Created on Thu Sep  1 13:26:53 2022

@author: DT
Hardware class to controll cryostat. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

import requests
import numpy as np
import json
from PyQt5 import QtCore
import time
from collections import defaultdict


class Cryocore(QtCore.QThread):
    name = 'cryostat'

    def __init__(self):
        super(Cryocore, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.set_T = []
        self.current_T = []
        self.stop = False
        self.parameter_dict['set_T'] = 10
        self.parameter_dict['current_T'] = 1
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['set_T']['val'] = 5
        self.parameter_display_dict['set_T']['unit'] = ' K'
        self.parameter_display_dict['set_T']['max'] = 1000
        self.parameter_display_dict['set_T']['read'] = False
        self.parameter_display_dict['current_T']['val'] = 5
        self.parameter_display_dict['current_T']['unit'] = ' K'
        self.parameter_display_dict['current_T']['max'] = 1000
        self.parameter_display_dict['current_T']['read'] = True

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

    def update_set_T(self, set_temperature):
        # set temperature to some degree K
        requests.put("http://10.131.3.6:47101/v1/controller/properties/platformTargetTemperature",json = {"platformTargetTemperature": set_temperature})

        print(f'Temperature set to {set_temperature}')

    def start_cool(self):
        # start chamber cooldown
        requests.post('http://10.131.3.6:47101/v1/controller/methods/cooldown()')

        print("Cooldown has started")

    def start_warm(self):
        # warmup the chamber
        requests.post('http://10.131.3.6:47101/v1/controller/methods/warmup()')
        print("Warming Up")

    def update_temp(self, new_T):
        self.parameter_dict['current_T'] = new_T


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

