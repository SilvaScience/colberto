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
def extract_impedances(times,voltages_in,voltages_out,freqs,resistance):
    '''
    Extracts the impedances from a frequency sweep
    input:
        time: time in sec for the oscilloscope data
        voltages_in: voltages measured at the output of the function generation (V)
        voltages_out: voltages measured at the terminals of the test load
        freqs: frequencies of the signal applied to the system (Hz)
        resistance: value of the test load 
    output:
        impedances: array of impedances extracted from the measurement
    '''
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
    return np.array(impedances)

if __name__=="__main__":
    plt.figure(0)
    #times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/piezo_free_16_05_impedance_measurement.h5')
    #impedances=extract_impedances(times,voltages_in,voltages_out,freqs,resistance)
    #plt.semilogx(freqs,np.real(impedances),label='real, piezo')
    times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/piezo_3mm_no_damping15_17_impedance_measurement.h5')
    impedances=extract_impedances(times,voltages_in,voltages_out,freqs,resistance)
    plt.semilogx(freqs,np.real(impedances),label='3mm mirror')
   # #plt.semilogx(freqs,np.imag(impedances),label='imag_beforetight')
    times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/piezo_3mm_tighter_no_damping15_48_impedance_measurement.h5')
    impedances=extract_impedances(times,voltages_in,voltages_out,freqs,resistance)
    plt.semilogx(freqs,np.real(impedances),label='real, 3mm mirror tighter')
    times,voltages_in,voltages_out,freqs,resistance=load_freqsweep('/home/thouin/Documents/Repo/colberto/piezo_3mm_damping16_55_impedance_measurement.h5')
    impedances=extract_impedances(times,voltages_in,voltages_out,freqs,resistance)
    plt.semilogx(freqs,np.real(impedances),label='real, 3mm mirror damper')
    #plt.semilogx(freqs,np.imag(impedances),label='imag')
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Real Impedance [Ohms]')
    plt.legend()
    impedances=np.array(impedances)
    admittances=1./impedances
    plt.figure(1)
    plt.semilogx(freqs,np.real(admittances),label='real')
    plt.semilogx(freqs,np.imag(admittances),label='imag')
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Admittance [mhos]')
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

