import numpy as np
from matplotlib import pyplot as plt


def mode_frequency(lambsquare,nu,E,h,density,a):
    '''
    Computes the frequency of a vibrational mode for a circular clamped thick plate
    
    :param lambsquare: lambda squared as described in Table 2.1 of Lessa 1969 Vibration of plates
    :param nu: Poisson's ratio
    :param E: Young's modulus
    :param h: Plate thickness
    :param density: Volume density of the plate
    :param a: Radius of the plate


    returns nu_vib: the vibration frequency of the plate in Hz
    '''
    D=E*h**3/(12*(1-nu**2))
    rho=density*h#Converts to area density
    nu_vib=1/(2*np.pi)*lambsquare/np.sqrt(rho/D)/a**2
    return nu_vib

if __name__=="__main__":
    lambsquares=[10.22,21.26,34.88,39.771,51.04]
    indices=['0-0','0-1','0-2','1-0','0-3']
    a=12.54e-3
    #For fused silica
    h=1e-3*np.linspace(1,8,50)
    E=75e6 # GPa=10^6 kg m-1s-2, from accuratus
    nu=0.17 # Poisson's ratio, from accuratus
    volume_density=2.2 # g per cm3
    volume_density=volume_density*1e-3/(1e-6)#convert to kg m-3 
    plt.figure()
    [plt.plot(1e3*h,mode_frequency(lambsquare=lambsquare,nu=nu,E=E,h=h,density=volume_density,a=a),label=indice) for (lambsquare,indice) in zip(lambsquares,indices)]
    plt.legend(title='(n-s)')
    plt.xlabel('Slab thickness (mm)')
    plt.ylabel('Resonnance frequency (Hz)')
    plt.show()
