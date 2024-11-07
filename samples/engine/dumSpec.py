import numpy as np

class dumSpec1000:
    def __init__(self,intTime=10e-3):
        self.intTime=intTime
        self.pixnum=1024
    
    def set_integration_time(self,t):
        self.intTime=t
    
    def get_integration_time(self):
        return self.intTime