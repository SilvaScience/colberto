import numpy as np
from matplotlib import pyplot as plt
import h5py
from scipy.optimize import curve_fit
def load_freqsweep(filename):
    '''
    Loads the frequency sweep from H5 file
    
    :param filename: Path to the file
    '''
    times=[]
    voltages_in=[]
    voltages_out=[]
    freqs=[]
    with h5py.File(filename,'r') as f:
        resistance=f['resistance'][()]
        for key in f['data'].keys():
            voltages_in.append(f['data'][key][0,:])
            voltages_out.append(f['data'][key][1,:])
            times.append(f['data'][key][2,:])
            freqs.append(f['data'][key].attrs['freq'])
    indices=np.argsort(freqs)
    freqs=[freqs[index] for index in indices]
    voltages_in=[voltages_in[index] for index in indices]
    voltages_out=[voltages_out[index] for index in indices]
    times=[times [index] for index in indices]
    return times,voltages_in,voltages_out,freqs,resistance
def sinusoid(x,a,b,c,d):
    '''
    Sinusoid function to fit to data of form a*sin(b*x+c)+d
    
    :param x: independant variable 
    :param params: params of a*sin(b*x+c)+d as a tuple (a,b,c,d) 
    '''
    return a*np.sin(2*np.pi*b*x+c)+d
if __name__=="__main__":
    times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/piezo_18:37_impedance_measurement.h5')
    impedances=[]
    for index,freq in enumerate(freqs):
        print(freqs[index])
        popt_in,pcov=curve_fit(sinusoid,times[index],voltages_in[index], bounds=[[0,0.95*freqs[index],-np.pi,-0.1],[20,1.05*freqs[index],np.pi,0.1]])
        popt_out,pcov=curve_fit(sinusoid,times[index],voltages_out[index], bounds=[[0,0.95*freqs[index],-2*np.pi,-0.1],[20,1.05*freqs[index],2*np.pi,0.1]])
        #print(index)
        #print(popt_out)
        impedance=((popt_in[0]/popt_out[0])*np.exp(1j*(popt_in[2]-popt_out[2]))-1)*resistance
        #print(impedance)
        impedances.append(impedance)
        #plt.figure()
        #plt.plot(times[index],voltages_in[index],label='voltages in')
        #plt.plot(times[index],sinusoid(times[index],*popt_in),label='fit')
        #plt.title('Voltage in, freq %.2e'%freq)
        #plt.xlabel('Time since epoch')
        #plt.figure()
        #plt.title('Voltage test load (%.0f ohms) freq %.2e'%(resistance,freq))
        #plt.xlabel('Time since epoch')
        #plt.plot(times[index],voltages_out[index],label='voltage out')
        #plt.plot(times[index],sinusoid(times[index],*popt_out),label='fit')
    plt.figure()
    plt.semilogx(freqs,np.real(impedances),label='real')
    plt.semilogx(freqs,np.imag(impedances),label='imag')
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Impedance [Ohms]')
    plt.legend()
    fig,axs=plt.subplots(2,1,sharex='col')
    axs[0].plot(freqs,np.abs(impedances))
    axs[0].set_ylabel('R (V)')
    axs[1].plot(freqs,np.angle(impedances,deg=True))
    axs[1].set_ylabel('$\phi$')
    axs[1].set_xlabel('Frequency (Hz)')
    axs[0].set_xscale('log')
    [ax.grid(which='Major', linestyle='-') for ax in axs]
    [ax.grid(which='Minor', linestyle=':') for ax in axs]
    plt.legend()
    plt.show()

