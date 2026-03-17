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
def Z_piezo(k,C0,R1,L1,C1,f):
    '''
        Inverse model of impedance of a piezoelectric transducer (inverse model of Equivalent piezoelectric actuator circuits and comparison 10.1109/AIM.2014.6878082)
        input:
            k: Inverse parameter of inverse resistance(ohm)
            C0: Piezo dielectric capacitance (Farad)
            R1: Piezo mechnical Resistance (ohm)
            L1: Piezo mechanical Inductance (Henry)
            C1: Piezo mechanical capacitance (Farad)
            f: frequency (Hz)
    '''
    Zp=para(Z_C(C0,f)+R_inverse(k,f),Z_L(L1,f)+Z_C(C1,f)+R1)
    return Zp
def R_inverse(k,f):
    '''
        Impedance of inverse resistor (inverse model of Equivalent piezoelectric actuator circuits and comparison 10.1109/AIM.2014.6878082)
        input:
            nu: frequency (Hz)
            k: inverse proportionnality constant
        output:
            R: impedance
    '''
    return k/(2*np.pi*f)
def Z_RLC(R,L,C,f):
    '''
        R: Piezo mechnical Resistance (ohm)
        L: Piezo mechanical Inductance (Henry)
        C: Piezo mechanical capacitance (Farad)
        f: frequency (Hz)
    '''
    Z=Z_L(L,f)+Z_C(C,f)+R
    return Z


if __name__=='__main__':
    f=np.logspace(4,7,2000)
    C1=0.04e-6
    L1=0.00001
    R1=1
    k=3e6
    C0=0.04e-6
    Zp=Z_piezo(k,C0,R1,L1,C1,f)
    Rr=0.1
    Lr=2e-6
    Cr=2e-6
    print('Resonnator frequency:%.2e Hz'%(1./(2*np.pi*np.sqrt(Lr*Cr))))
    Zr=Z_RLC(Rr,Lr,Cr,f)
    fig,axs=plt.subplots(2,1,sharex='col')
    axs[0].semilogx(f,np.real(Zp))
    axs[1].semilogx(f,np.imag(Zp))
    axs[1].set_xlabel('Frequency [Hz]')
    axs[0].set_ylabel('Real impedance [Ohms]')
    axs[1].set_ylabel('Imag. impedance [Ohms]')
    axs[0].set_title('Piezo')
    fig,axs=plt.subplots(2,1,sharex='col')
    axs[0].semilogx(f,np.real(1./Zr))
    axs[1].semilogx(f,np.imag(1./Zr))
    axs[1].set_xlabel('Frequency [Hz]')
    axs[0].set_ylabel('Real Admittance [mhos]')
    axs[1].set_ylabel('Imag. Admittance [mhos]')
    axs[0].set_title('Resonnator')

    Z_com=para(Zp,Zr)
    fig,axs=plt.subplots(2,1,sharex='col')
    axs[0].loglog(f,np.real(Zp),label='Piezo')
    axs[1].semilogx(f,np.imag(Zp))
    axs[0].loglog(f,np.real(Z_com),label='Single resonnator')
    axs[1].semilogx(f,np.imag(Z_com))
    axs[1].set_xlabel('Frequency [Hz]')
    axs[0].set_ylabel('Real impedance [Ohms]')
    axs[1].set_ylabel('Imag. impedance [Ohms]')

    Z_com_2=para(para(Zp,Zr),Zr)
    axs[0].loglog(f,np.real(Z_com_2),label='Dual resonnator (full parallel)')
    axs[1].semilogx(f,np.imag(Z_com_2))

    Z_com_2=para(Zp+Zr,Zr)
    axs[0].loglog(f,np.real(Z_com_2),label='Dual resonnator (series, parallel)')
    axs[1].semilogx(f,np.imag(Z_com_2))
    axs[0].legend()

    plt.show()