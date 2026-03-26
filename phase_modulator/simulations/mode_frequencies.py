import numpy as np
from matplotlib import pyplot as plt
from scipy.special import jv,iv

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
            :param n: Number of axial nodes (theta)
            :param s: Number of radial nodes (r)
            :param r: radial position (m)
            :param theta: angular position (rad)
            
            returns Wns
        '''
        k=np.sqrt(self.lambsquare[n,s])/self.a
        Wns=((-iv(n,k*self.a)/jv(n,k*self.a))*jv(n,k*r)+iv(n,k*r))*np.cos(n*theta)
        Wns=Wns*np.where(r>=self.a,np.nan,1)
        return Wns
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
def lambsquares(n):
        '''
            Finds the eigenvalues determining the frequencies of the plate probme (roots of eq 2.5 of Leissa) 
        '''
        fun=lambda x: jv(n,x)*iv(n+1,x)+iv(n,x)*jv(n+1,x)
        return n

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
    fused_silica_3mm.mode_profile(n=1,s=1)
    plt.title('n=1,s=1')
    plt.show()
