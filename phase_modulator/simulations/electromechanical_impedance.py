import numpy as np
from matplotlib import pyplot as plt

def para(Z1,Z2):
    '''
        Parallel composition of two impedances Z1 and Z2
        Input:
            Z1: impdance 1
            Z2: impdance 2
        output:
            Zo: parallel impedance
    '''
    return 1./(1./Z1+1./Z2)

def Z_C(C,f):
    '''
    Impedance of a capacitor (C)
    input:
        C: Capacitance (Farad)
        f: frequency (Hz)
    output:
        Zc impedance of the capacitor (ohms)
    '''
    return 1./(1j*2*np.pi*C*f)

def Z_L(L,f):
    '''
    Impedance of an inductor (L)
    input:
        L: Inductance (Henry)
        f: frequency (Hz)
    output:
        Zc impedance of the inductor(ohms)
    '''
    return 1j*2*np.pi*L*f
def Z_RLC(R,L,C,f):
    '''
        Impedance of a RLC circuit
        input:
            R: Resistance (ohm)
            L: Inductance (Henry)
            C: Capacitance (Farad)
            f: frequency (Hz)
    '''
    s=2j*np.pi*f
    Z=R+L*s+1./(C*s)
    return Z

if __name__=='__main__':
    f=np.logspace(4,6,2000)
    C1=0.04e-6
    L1=0.00001
    R1=1
    C0=0.04e-6
    Zp=para(Z_C(C0,f),Z_L(L1,f)+Z_C(C1,f)+R1)
    plt.figure()
    plt.semilogx(f,np.real(Zp))
    #plt.semilogx(f,np.imag(Zp))
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Impedance [Ohms]')
    plt.show()