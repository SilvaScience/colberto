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
    return times,voltages_in,voltages_out,freqs,resistance
def sinusoid(x,a,b,c,d):
    '''
    Sinusoid function to fit to data of form a*sin(b*x+c)+d
    
    :param x: independant variable 
    :param params: params of a*sin(b*x+c)+d as a tuple (a,b,c,d) 
    '''
    return a*np.sin(2*np.pi*b*x+c)+d
if __name__=="__main__":
    times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/47kresistor_15:29_impedance_measurement.h5')
    plt.figure()
    index=4
    print(freqs[index])
    plt.plot(times[index],voltages_in[index],label='voltages in')
    popt_in,pcov=curve_fit(sinusoid,times[index],voltages_in[index], bounds=[[0,0.5*freqs[index],-np.pi,-0.1],[10,2*freqs[index],np.pi,0.1]])
    plt.plot(times[index],sinusoid(times[index],*popt_in),label='fit')
    plt.title('Voltage in')
    plt.xlabel('Time since epoch')
    plt.figure()
    plt.title('Voltage test load (%.0f ohms)'%resistance)
    plt.xlabel('Time since epoch')
    plt.plot(times[index],voltages_out[index],label='voltage out')
    popt_out,pcov=curve_fit(sinusoid,times[index],voltages_out[index], bounds=[[0,0.5*freqs[index],-np.pi,-0.1],[10,2*freqs[index],np.pi,0.1]])
    plt.plot(times[index],sinusoid(times[index],*popt_out),label='fit')
    impedance=((popt_in[0]/popt_out[0])*np.exp(1j*(popt_in[2]-popt_out[2]))-1)*resistance
    plt.legend()
    plt.show()
