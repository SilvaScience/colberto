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


    def initialisation(self):
        # Configuration de l'oscilloscope
        oscilloscope = OscilloscopeController()
    # Connexion à l'oscilloscope
        oscilloscope.connect()
    # Configurer la source et le format de la forme d'onde
        oscilloscope.set_waveform_source('CHAN1')
        oscilloscope.set_waveform_format('ASC')



"""
    A class to control a Keysight Oscilloscope via a network connection using the PyVISA library.

    This class provides methods to connect to the oscilloscope, configure waveform acquisition 
    settings, and manage the connection. The oscilloscope is accessed via its IP address over a 
    TCP/IP connection.

    Attributes:
    -----------
    ip_address : str
        The IP address of the oscilloscope.
    timeout : int
        The timeout duration for communication with the oscilloscope in milliseconds.
    rm : pyvisa.ResourceManager
        The PyVISA resource manager used to handle the VISA resources.
    oscilloscope : pyvisa.resources.Resource
        The VISA resource representing the connected oscilloscope.

    Methods:
    --------
    connect():
        Establishes a connection to the oscilloscope using the specified IP address 
        and configures the timeout and clears any previous settings.

    set_waveform_source(channel='CHAN1'):
        Sets the waveform acquisition source on the oscilloscope, with the default 
        channel being 'CHAN1'.

    set_waveform_format(format='ASC'):
        Configures the output format of the waveform data to be retrieved from the oscilloscope, 
        with the default format being ASCII ('ASC').

    close():
        Closes the connection to the oscilloscope if it is currently open.

    initialisation():
        Initializes the oscilloscope by creating an instance of OscilloscopeController, 
        establishing the connection, and setting the waveform source and format to 
        default values ('CHAN1' and 'ASC' respectively).
"""