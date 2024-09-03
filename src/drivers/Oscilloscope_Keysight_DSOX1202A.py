import pyvisa

ip_address='169.254.75.129'
class OscilloscopeController:
    def __init__(self, timeout=10000):
        self.ip_address = ip_address
        self.timeout = timeout
        self.rm = pyvisa.ResourceManager('@py')
        self.oscilloscope = None

    def connect(self):
        self.oscilloscope = self.rm.open_resource(f'TCPIP0::{self.ip_address}::inst0::INSTR')
        self.oscilloscope.timeout = self.timeout
        self.oscilloscope.clear()

    def set_waveform_source(self, channel='CHAN1'):
        self.oscilloscope.write(f':WAV:SOURCE {channel}')

    def set_waveform_format(self, format='ASC'):
        self.oscilloscope.write(f':WAV:FORM {format}')

    def close(self):
        if self.oscilloscope is not None:
            self.oscilloscope.close()