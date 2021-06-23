# SD AWG M3202A
from colorama import init, Fore, Back
init(autoreset=True) #to convert termcolor to wins color
from os.path import basename as bs
mdlname = bs(__file__).split('.')[0] # module's name e.g. PSG

from numpy import array, zeros, ceil, empty, float32, pad
from pyqum.instrument.logger import address, set_status
from pyqum.instrument.analyzer import curve
from pyqum.instrument.composer import pulser

# SD1 Libraries
import sys
sys.path.append(r'C:\\Program Files (x86)\\Keysight\SD1\\Libraries\\Python')
from pyqum.API.KeySight import keysightSD1

# INITIALIZATION
def Initiate(which, mode='DATABASE', current=False):
    ad = address(mode)
    rs = ad.lookup(mdlname, label=int(which)) # Instrument's Address
    try:
        # CREATE AND OPEN MODULE
        module = keysightSD1.SD_AOU()
        moduleID = module.openWithSlot("", int(rs.split('::')[0]), int(rs.split('::')[1])) # PRODUCT, CHASSIS::SLOT
        if moduleID < 0: print(Fore.RED + "Module open error:", moduleID)
        else: print(Fore.GREEN + "%s-%s's connection Initialized >> ID: %s, Name: %s, Chassis: %s, Slot: %s" % (mdlname,which, moduleID, module.getProductName(), module.getChassis(), module.getSlot()))
        
        if current:
            # PENDING: multi-channel DC
            print(Fore.YELLOW + "DC mode for DAC (only channel-1 will be used)")
            module.channelWaveShape(int(current), keysightSD1.SD_Waveshapes.AOU_HIZ)

        set_status(mdlname, dict(state='connected'), which)
        ad.update_machine(1, "%s_%s"%(mdlname,which))
    except: 
        set_status(mdlname, dict(state='DISCONNECTED'), which)
        print(Fore.RED + "%s-%s's connection NOT FOUND" %(mdlname,which))
        # module = "disconnected"
    return module

# FUNCTIONS
def triggerio(module, direction):
    '''get direction and sync from index of combo-boxes
    direction: 0: output, 1: input
    '''
    return module.triggerIOconfig(int(direction))
def run(module, channels=[1,2,3,4]):
    mask = 0
    for ch in channels: mask += 2**(ch-1)        
    return module.AWGstartMultiple(mask)
def stop(module, channels=[1,2,3,4]):
    mask = 0
    for ch in channels: mask += 2**(ch-1)        
    return module.AWGstopMultiple(mask)
def triggerall(module, last_channel):
    nMask = int(2**last_channel - 1) # mask to trigger up to the last channel
    return module.AWGtriggerMultiple(nMask)
def waveshape(module, channel, shape):
    '''
    ALL shapes:
    HiZ*        The output signal is set to HIZ. No output signal is provided:              AOU_HIZ -1
    No Signal   The output signal is set to 0. All other channel settings are maintained:   AOU_OFF (default) 0
    Sinusoidal  Generated by the Function Generator:                                        AOU_SINUSOIDAL 1
    Triangular  Generated by the Function Generator:                                        AOU_TRIANGULAR 2
    Square      Generated by the Function Generator:                                        AOU_SQUARE 4
    DC Voltage  Generated by the Amplitude Modulator:                                       AOU_DC 5
    AWG         Generated by the Arbitrary Waveform Generator (See AWG Waveform Types):     AOU_AWG 6
    Partner CH  EVEN channel set as a partner to the previous ODD channel:                  AOU_PARTNER 8
    ''' 
    return module.channelWaveShape(channel, shape)
def amplitude(module, channel, value):
    '''value in volts (–1.5 V to 1.5 V)
    '''
    return module.channelAmplitude(channel, value)
def frequency(module, channel, value):
    '''value in Hz. (Refer to the product’s Data Sheet for frequency specifications.)
    '''
    return module.channelFrequency(channel, value)
def phase(module, channel, value):
    '''value in degrees. (Refer to the product’s Data Sheet for phase specifications.)
    '''
    return module.channelPhase(channel, value)
def offset(module, channel, value):
    '''value in volts (–1.5 V to 1.5 V)
    '''
    return module.channelOffset(channel, value)
def configureExternalTrigger(module, channel, extSource, trigBehavior=4, sync=1):
    """Configure external trig for given channel
    extSource:    0 EXT, 4000-4007 PXI-PXI7
    trigBehavior: 1 HIGH, 2 LOW, 3 RISE, 4 FALL
    sync:         0 NO-CLK, 1 10-CLK
    """
    return module.AWGtriggerExternalConfig(channel, int(extSource), int(trigBehavior), int(sync))
def clearOldWaveforms(module):
    """Flush AWG queue and remove all cached waveforms"""
    return module.waveformFlush()

def sendWaveform(module, waveform_id, data=None):
    """Send waveform marked by waveform_id to AWG channel:
    """
    wave = keysightSD1.SD_Wave()
    waveformType = 0
    wave.newFromArrayDouble(waveformType, data)
    stat = module.waveformLoad(wave, waveform_id)
    if stat < 0: print('Send error:', keysightSD1.SD_Error.getErrorMessage(stat))
    return waveform_id
def resendWaveform(module, waveform_id, data=None):
    """ReSend waveform marked by waveform_id to AWG channel: ONLY data of the same length can replace each other
    """
    wave = keysightSD1.SD_Wave()
    waveformType = 0
    wave.newFromArrayDouble(waveformType, data)
    stat = module.waveformReLoad(wave, waveform_id)
    if stat < 0: print('ReSend error:', keysightSD1.SD_Error.getErrorMessage(stat))
    return waveform_id
def queueWaveform(module, channel, waveform_id, trigMode=0, delay=0, cycles=0, prescaler=0):
    """Queue waveform to AWG channel
    trigMode:  AUTOTRIG 0, SWHVITRIG 1, SWHVITRIG_CYCLE 5, EXTTRIG 2, EXTTRIG_CYCLE 6
    delay:     Defines the delay between the trigger and the waveform launch, in 10ns
    cycles:    Number of times the waveform is played once launched. (Zero specifies infinite cycles).
    prescaler: Waveform prescaler value, to reduce the effective sampling rate by prescaler x 5.
    """
    stat = module.AWGqueueWaveform(channel, waveform_id, trigMode, delay, cycles, prescaler)
    if stat < 0: print('Queue error:', keysightSD1.SD_Error.getErrorMessage(stat))
    return stat
def processWaveform(module, channel,):
    '''
    WAVEFORM FROM ARRAY/LIST: This function is equivalent to create a waveform with new, and then to call waveformLoad, AWGqueueWaveform and AWGstart
    '''
    stat = module.AWGfromArray(channel, 0, 0, 0, 0, 0, data)
    return stat
    
def configureMarker(module, channel, active_pxi_trgline=[2], trgIOmask=1, markerMode=3, markerValue=0, syncMode=1, length=731, delay=0):
    """Configure marker for given channel, must be done after queueing
    markerMode          0: ‘Disabled’, 1: ‘On Start Event (when Start trigger is received)’, 2: ‘On First Sample of Waveform (after WF startDelay)’, 3: ‘On Every Cycle’.
    active_pxi_trgline  Array of active PXI trigger lines, ex: [0,1,2]
    trgIOmask           Mask to select front-panel triggers to use. 'bit0': TriggerIO and so on.
    markerValue         0: ‘Low’, 1: ‘High’. Note that PXItrigger are active low signals, ‘1’ will generate a ‘0’ pulse.
    syncMode            ‘0’ is synchronized to CLKsys and ‘1’ is synchronized to 10 MHz reference clock.
    length              Pulse length of the marker, in units of nanoseconds. Enter the value of length as a multiple of 10. For example, if you enter 30, it is considered as 30ns.
    delay               Delay to add before the marker pulse. (markerMode selects the start point of the marker, after which the delay is added).
    """
    trgPXImask = 0 # initial PXI trigger mask
    for i in active_pxi_trgline: trgPXImask += 2**i
    print("Trigger PXI Mask: %s" %trgPXImask)
    # configure
    stat = module.AWGqueueMarkerConfig(nAWG=channel, markerMode=markerMode, trgPXImask=trgPXImask,
                                    trgIOmask=trgIOmask, value=markerValue, syncMode=syncMode,
                                    length=length, delay=delay)
    if stat < 0: print('Marker error:', keysightSD1.SD_Error.getErrorMessage(stat))
    return stat


# Composite functions for directives:
def prepare_DAC(module, channel, maxlevel=1.5, trigbyPXI=2, mode=1, sync=1):
    '''
    maxlevel: -1.5V to 1.5V
    trigbyPXI: 0 to 7 (out-of-range value: EXT)
    portDirection: 0: output, 1: input
    mode: ‘0’ indicates ‘One shot’ and ‘1’ indicates ‘Cyclic’
    sync:         0 NO-CLK, 1 10-CLK
    '''
    if int(trigbyPXI) in range(8): extSource, portDirection = 4000+int(trigbyPXI), 0
    else: extSource, portDirection = 0, 1

    triggerio(module, portDirection) # Trigger-IO port-direction
    waveshape(module, channel, keysightSD1.SD_Waveshapes.AOU_AWG) # Arbitrary Shape for DAC
    amplitude(module, channel, maxlevel) # Maximum amplitude in V
    module.AWGqueueConfig(channel, mode) # Operation-mode of the queue 
    configureExternalTrigger(module, channel, extSource, keysightSD1.SD_TriggerBehaviors.TRIGGER_FALL, sync) # Only FALL works: PXItrigger are active low signals
    return module
def compose_DAC(module, channel, pulsedata, markerMode=0, trgIOmask=0, markerValue=0, clearALL=False):
    if clearALL: clearOldWaveforms(module)
    sendWaveform(module, 0, pulsedata)
    queueWaveform(module, channel, 0, keysightSD1.SD_TriggerModes.EXTTRIG)
    configureMarker(module, channel, markerMode, trgIOmask, markerValue)
    run(module, [1,channel])
    
    return module

# Dedicated for DC-sweep:
def output(module, state):
    if state:
        offset(module, 1, 0)
        run(module, [1])
    else: stop(module, [1])
    return state
def sweep(module, dcvalue):
    '''DC amplitude in volts (–1.5 V to 1.5 V)
    '''
    module.channelWaveShape(1, keysightSD1.SD_Waveshapes.AOU_DC)
    status = module.channelAmplitude(1, float(dcvalue))
    return status


def close(module, which, reset=True, mode='DATABASE'):
    if reset:
        module.waveformFlush() # clear all old-waveforms in RAM
        for i in range(4): 
            module.AWGstop(i+1) # stop awg
            module.AWGflush(i+1)
            module.channelWaveShape(i+1, -1) # -1: HiZ
        set_status(mdlname, dict(config='reset'), which)
    else: set_status(mdlname, dict(config='previous'), which)
    try:
        module.close() #None means Success?
        status = "Success"
        ad = address(mode)
        ad.update_machine(0, "%s_%s"%(mdlname,which))
    except: status = "Error"
    set_status(mdlname, dict(state='disconnected: %s' %status), which)
    print(Back.WHITE + Fore.BLACK + "%s's connection Closed: %s" %(mdlname,status))
    return status


# Test Zone
def test():

    # INITIATION:
    m1 = Initiate(1, 'TEST')
    m2 = Initiate(2, 'TEST')
    # m3 = Initiate(current=True, which=3, mode='TEST') # DC

    # PREPARATION:
    prepare_DAC(m1, 3, maxlevel=1.5, trigbyPXI=2, mode=1, sync=1)
    prepare_DAC(m2, 1, maxlevel=1.5, trigbyPXI=2, mode=1, sync=1)
    prepare_DAC(m2, 3, maxlevel=1.5, trigbyPXI=2, mode=1, sync=1)
    
    # COMPOSITION:
    input("Any key to RUN 1st WAVE from AWG-1: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,370,0;FLAT/,100000,0.95;")
    pulseq.song()
    # pulseq.
    clearOldWaveforms(m1)
    sendWaveform(m1, 0, pulseq.music)
    queueWaveform(m1, 3, 0)
    configureMarker(m1, 3, markerMode=3, trgIOmask=0, markerValue=0)
    run(m1, [3])
    
    input("Any key to RUN 2nd WAVE from AWG-1: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,370,0;FLAT/,300000,0.95;")
    pulseq.song()
    # clearOldWaveforms(m1)
    resendWaveform(m1, 0, pulseq.music)
    # queueWaveform(m1, 3, 0)
    # configureMarker(m1, 3, markerMode=3, trgIOmask=0, markerValue=0)
    run(m1, [3])

    input("Any key to RUN 3rd WAVE from AWG-1: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,370,0;FLAT/,500000,0.95;")
    pulseq.song()
    # clearOldWaveforms(m1)
    resendWaveform(m1, 0, pulseq.music)
    # queueWaveform(m1, 3, 0)
    # configureMarker(m1, 3, markerMode=3, trgIOmask=0, markerValue=0)
    run(m1, [3])

    # m2.triggerIOread()
    input("Any key to RUN 1st WAVE from AWG-2: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,100000,0.95;")
    pulseq.song()
    clearOldWaveforms(m2)
    # ch-1
    sendWaveform(m2, 0, pulseq.music)
    queueWaveform(m2, 1, 0, keysightSD1.SD_TriggerModes.EXTTRIG)
    # ch-3
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,200000,0.95;")
    pulseq.song()
    sendWaveform(m2, 1, pulseq.music)
    queueWaveform(m2, 3, 1, keysightSD1.SD_TriggerModes.EXTTRIG)
    configureMarker(m2, 3, markerMode=0, trgIOmask=0, markerValue=0)
    run(m2, [1,3])

    input("Any key to RUN 2nd WAVE from AWG-2: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,300000,0.95;")
    pulseq.song()
    clearOldWaveforms(m2)
    # ch-1
    sendWaveform(m2, 0, pulseq.music)
    queueWaveform(m2, 1, 0, keysightSD1.SD_TriggerModes.EXTTRIG)
    # ch-3
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,400000,0.95;")
    pulseq.song()
    sendWaveform(m2, 1, pulseq.music)
    queueWaveform(m2, 3, 1, keysightSD1.SD_TriggerModes.EXTTRIG)
    configureMarker(m2, 3, markerMode=0, trgIOmask=0, markerValue=0)
    run(m2, [1,3])

    input("Any key to RUN 3rd WAVE from AWG-2: ")
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,500000,0.95;")
    pulseq.song()
    clearOldWaveforms(m2)
    # ch-1
    sendWaveform(m2, 0, pulseq.music)
    queueWaveform(m2, 1, 0, keysightSD1.SD_TriggerModes.EXTTRIG)
    # ch-3
    pulseq = pulser(dt=2, clock_multiples=1, score="ns=1000000;FLAT/,600000,0.95;")
    pulseq.song()
    sendWaveform(m2, 1, pulseq.music)
    queueWaveform(m2, 3, 1, keysightSD1.SD_TriggerModes.EXTTRIG)
    configureMarker(m2, 3, markerMode=0, trgIOmask=0, markerValue=0)
    run(m2, [1,3])
    
    # DC test:
    # output(m3, 1)
    # dcvalues = [0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.15]
    # for val in dcvalues:
    #     input("Any key to output DC=%sV from AWG-3: " %val)
    #     sweep(m3, str(val))

    # CLOSING:
    input("Any key to CLOSE AWG-1: ")
    close(m1, 1, True, 'TEST')
    input("Any key to CLOSE AWG-2: ")
    close(m2, 2, True, 'TEST')
    # input("Any key to CLOSE AWG-3: ")
    # close(m3, 3, True, 'TEST')

    return

# test()