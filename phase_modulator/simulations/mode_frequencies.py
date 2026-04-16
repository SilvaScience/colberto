import numpy as np
from matplotlib import pyplot as plt
from scipy.special import jv,iv,jvp,ivp

class vibratingPlate():
    '''
        Class describing a vibrating plate
    '''
    def __init__(self,nu,E,h,rho,a):
        '''
        Initializes a plate with physical parameters
            :param nu: Poisson's ratio
            :param E: Young's modulus
            :param h: Plate thickness
            :param rho: Volume density of the plate
            :param a: Radius of the plate
        '''
        self.a=a
        self.E=E
        self.rho=rho
        self.nu=nu
        self.h=h
        self.lambsquare=np.array([[10.2168,21.26,34.88,51.04,69.6659,90.73,114.2126],
                                 [39.771, 60.82, 84.68, 111.01, 140.1079, 171.8029,206.0706],
                                 [89.104,120.08,153.81,190.30,229.5186,271.4283,316.0015]])# Values from Leissa table 2.1
                            
    def mode_frequency(self,n,s):
        '''
        Computes the frequency of a vibrational mode for a circular clamped thick plate
        
        :param n: Number of axial nodes (theta)
        :param s: Number of radial nodes (r)


        returns nu_vib: the vibration frequency of the plate in Hz
        '''
        self.D=self.E*self.h**3/(12*(1-self.nu**2))
        self.a_rho=self.rho*self.h#Converts to area density
        nu_vib=1/(2*np.pi)*self.lambsquare[n,s]/np.sqrt(self.a_rho/self.D)/self.a**2
        return nu_vib
    def Wns(self,n,s,r,theta):
        '''
            Computes the mode profile at radius r and angle theta for a mode indices n and s 
            :param n: Number of axial nodes (along theta)
            :param s: Number of radial nodes (along r)
            :param r: radial position (m)
            :param theta: angular position (rad)
            
            returns Wns
        '''
        k=np.sqrt(self.lambsquare[n,s])/self.a
        Wns=((-iv(n,k*self.a)/jv(n,k*self.a))*jv(n,k*r)+iv(n,k*r))*np.cos(n*theta)
        Wns=Wns*np.where(r>=self.a,np.nan,1)
        return Wns
    
    def Xi(self,n,s,nu,r_0,theta_0):
        '''
            Computes the response of a mode of indices n,s to a force at frequency nu applied at rho_0 and theta_0.
            The response is normalized by the time dependant force 
            :param n: Number of axial nodes (along theta)
            :param s: Number of radial nodes (along r)
            :param nu: frequency (Hz) of the force 
            :param r_0: radial position of the force (m)
            :param theta_0: angular position (rad) of the force 

            returns Xi_n,s(r_0,theta_0)

        '''
        kns2=self.lambsquare[n,s]/self.a**2
        print(kns2)
        k2=2*np.pi*nu*np.sqrt(self.a_rho/self.D)
        print(k2)
        Ans=np.abs(iv(n,self.lambsquare[n,s])/jv(n,self.lambsquare[n,s]))**2*(self.a**2/2)*np.abs(jvp(n,self.lambsquare[n,s]))**2+(self.a**2/2)*np.abs(ivp(n,self.lambsquare[n,s]))**2
        Xins=(self.Wns(n,s,r_0,theta_0))/((kns2-k2)*(kns2+k2)*Ans)
        return Xins

    def mode_profile(self,n,s):
        '''
            Plots the spatial profile at maximal ampltiude of a mode
            :param n: Number of axial nodes (theta)
            :param s: Number of radial nodes (r)

        returns mode: 2D np.array of tranverse deformation
                rho: mesh of rho values
                theta: mesh of theta values
        '''
        x=np.linspace(-self.a,self.a,100)
        y=np.linspace(-self.a,self.a,100)
        xx,yy=np.meshgrid(x,y)
        rho=np.sqrt(xx**2+yy**2) 
        theta=-np.atan(yy/xx)+np.pi/2
        theta=theta+np.where(xx<=0,np.pi,0)
        plt.imshow(self.Wns(n,s,rho,theta))
        plt.colorbar()

if __name__=="__main__":
    #indices=['0-0','0-1','0-2','1-0','0-3']
    a=12.54e-3
    #For fused silica
    h=3e-3
    E=75e9 # GPa=10^9 kg m-1s-2, from https://www.ineos.com/globalassets/ineos-group/businesses/ineos-olefins-and-polymers-usa/products/technical-information--patents/new/ineos-typical-engineering-properties-of-hdpe.pdf
    nu=0.17 # Poisson's ratio, from  https://www.ineos.com/globalassets/ineos-group/businesses/ineos-olefins-and-polymers-usa/products/technical-information--patents/new/ineos-typical-engineering-properties-of-hdpe.pdf
    volume_density=2.2 # g per cm3
    volume_density=volume_density*1e-3/(1e-6)#convert to kg m-3 
    fused_silica_3mm=vibratingPlate(nu=nu,E=E,h=h,rho=volume_density,a=a) 
    print("Resonnance frequency is : %.2e Hz"%fused_silica_3mm.mode_frequency(0,0))
    fused_silica_3mm.mode_profile(n=1,s=0)
    plt.title('n=1,s=1')
    nu=np.logspace(4,6,1000)
    r_0=a/2*0.75
    theta_0=0
    plt.figure()
    plt.title('r_0=a/2, theta_0=0')
    plt.loglog(nu,np.abs(fused_silica_3mm.Xi(0,0,nu,r_0=r_0,theta_0=theta_0)),label='n=0, s=0')
    plt.loglog(nu,np.abs(fused_silica_3mm.Xi(0,1,nu,r_0=r_0,theta_0=theta_0)),label='n=1, s=0')
    plt.loglog(nu,np.abs(fused_silica_3mm.Xi(1,0,nu,r_0=r_0,theta_0=theta_0)),label='n=0, s=1')
    plt.xlabel('Drive frequency (Hz)')
    plt.ylabel('Mode response')
    plt.legend()

    plt.show()
