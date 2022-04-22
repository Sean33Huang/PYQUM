# SD AWG M3202A
from colorama import init, Fore, Back
init(autoreset=True) #to convert termcolor to wins color
from os.path import basename as bs
mdlname = bs(__file__).split('.')[0] # module's name e.g. PSG

from numpy import zeros, ceil, where
from pyqum.instrument.logger import address, set_status
from pyqum.instrument.composer import pulser
from pyqum.instrument.toolbox import normalize_dipeak

# SD1 Libraries
import sys
# sys.path.append(r'C:\\Program Files (x86)\\Keysight\SD1\\Libraries\\Python')
import keysightSD1
# sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
# import keysightSD1
# print("INIT SDAWG...")

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
        
        if current: print(Fore.YELLOW + "DC-mode for DAC: ALL 4 channels (Dummy selection)") # to align with YOKO-DC
        for i in range(4): module.channelWaveShape(i+1, keysightSD1.SD_Waveshapes.AOU_HIZ) # always HiZ ALL 4-channels

        set_status(mdlname, dict(state='connected'), which)
        ad.update_machine(1, "%s_%s"%(mdlname,which))
    except: 
        set_status(mdlname, dict(state='DISCONNECTED'), which)
        print(Fore.RED + "%s-%s's connection NOT FOUND" %(mdlname,which))
        # module = "disconnected"
    return module

# FUNCTIONS
def model(module):
    return ["model", {"IDN": "%s (%s)" %(module.getProductName(), module.getSerialNumber())}]
def clock(module, action=['Get', '']):
    '''simulated SCPI: return clock-source & clock-rate'''
    if 'Set' in action:
        module.clockSetFrequency(action[2], 0) # 0: low-jitter, 1: fast-tune
    return ["Success", {"SOURce": module.clockGetSyncFrequency(), "SRATe": module.clockGetFrequency()}]
def triggerio(module, direction):
    '''get direction and sync from index of combo-boxes
    direction: 0: output, 1: input
    '''
    return module.triggerIOconfig(int(direction))
def runstate(module):
    '''This command returns the run-state of the AWG. (Query ONLY, Adapted from TKAWG)
        0 indicates that the AWG has stopped. 
        1 indicates that the AWG is waiting for trigger. 
        2 indicates that the AWG is running. (any channel will do)
    '''
    rstate = 0
    for i in range (4): rstate += int(module.AWGisRunning(i+1)) # Returns ‘1’ if the AWG is running or ‘0’ if it is stopped.
    rstate /= 4
    return ["runstate", {"RSTATE": ceil(rstate)*2}]
def ready(module, channels=[1,2,3,4]):
    '''Start ALL Channels by defaults'''
    mask = 0
    for ch in channels: mask += 2**(ch-1) 
    status = module.AWGstartMultiple(mask) 
    print(Fore.GREEN + "PLAYING MASK: %s" %mask)      
    return status
def play(module):
    '''A Dummy function To be compatible with TKAWG'''
    # print(Fore.YELLOW + "Waveform loading status: %s" %bool(keysightSD1.SD_Wave.getStatus))
    if bool(keysightSD1.SD_Wave.getStatus): return module.AWGnWFplaying(1)
def stop(module, channels=[1,2,3,4]):
    mask = 0
    for ch in channels: mask += 2**(ch-1)        
    return module.AWGstopMultiple(mask)
def alloff(module, action=['Set',1]):
    if int(action[1]):
        mask = 0
        for ch in [1,2,3,4]: mask += 2**(ch-1)   
        status = module.AWGstopMultiple(mask)
    else: status = -1     
    return status
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
def sourcelevel(module, channel, action=['Get','','']):
    '''value in volts (–1.5 V to 1.5 V)
    '''
    if 'Set' in action:
        module.channelAmplitude(channel, action[1])
        module.channelOffset(channel, action[2])
    return ["Defaults", {'AMPLITUDE': "1.5", "OFFSET": "0"}]
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
def clear_waveform(module, channel="ALL"):
    print(Fore.CYAN + "Flush AWG queue and remove %s cached waveforms"%channel)
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
def processWaveform(module, channel, data):
    '''
    WAVEFORM FROM ARRAY/LIST: This function is equivalent to create a waveform with new, and then to call waveformLoad, AWGqueueWaveform and AWGstart
    '''
    stat = module.AWGfromArray(channel, 0, 0, 0, 0, 0, data)
    return stat
def configureMarker(module, channel, active_pxi_trgline=[2], markerMode=3, trgIOmask=0, markerValue=0, syncMode=1, length=731, delay=0):
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
    # print("Trigger PXI Mask: %s" %trgPXImask)
    # configure
    stat = module.AWGqueueMarkerConfig(nAWG=channel, markerMode=markerMode, trgPXImask=trgPXImask,
                                    trgIOmask=trgIOmask, value=markerValue, syncMode=syncMode,
                                    length=length, delay=delay)
    if stat < 0: print('Marker error:', keysightSD1.SD_Error.getErrorMessage(stat))
    return stat


# Composite functions for directives:
def prepare_DAC(module, channel, datasize, maxlevel=1.5, update_settings={}):
    '''
    datasize: dummy-parameter to be compatible with TKAWG\n
    maxlevel: -1.5V to 1.5V\n
    trigbyPXI: 0 to 7 (negative-value: Front Trig I/O port)\n
    mode: ‘0’ indicates ‘One shot’ and ‘1’ indicates ‘Cyclic’\n
    sync:  0 NO-CLK, 1 10-CLK \n

    External Trigger options:\n
    External I/O Trigger: 0 (Card's Front 1st SMA-port)\n
    PXI Trigger [0 to n]: 4000 + Trigger No. (Chassis's Backplane)\n

    Default: 
    Master triggering PXI-2 lane\n
    Assign Ch-4 for PIN-SWITCH if and only if markeroption=7.\n

    REFERENCES:
    trigMode:  AUTOTRIG 0, SWHVITRIG 1, SWHVITRIG_CYCLE 5, EXTTRIG 2, EXTTRIG_CYCLE 6
    markerValue         0: ‘Low’, 1: ‘High’. Note that PXItrigger are active low signals, ‘1’ will generate a ‘0’ pulse. (i.e. 1: active-high, 0: active-low)
    trigBehavior:       1 HIGH, 2 LOW, 3 RISE, 4 FALL

    NOTE:
    1. Slave cannot produce marker output on either PXI or Trigger-I/O port without having some serious trigger instabilities!
    2. For inter-Slot alignment:\n
        a. Within 100ns: BOTH Master & Slave can play ALL 4 channels as long as clearQ is set to be True in Compose. (Not needed in Pre-Compose though.)
        b. Within 0ns (PERFECTO): Master can ONLY play up to 3 channels while Slave can play ALL 4 channels as long as clearQ is set to be True in Compose. (Not needed in Pre-Compose though.)
        c. If clearQ not used in Compose, resend-error might require the DAC be restarted.
    '''
    # 1. Loading the settings:
    settings=dict(trigbyPXI=2, mode=1, sync=1, markeroption=0, Master=True, markerdelay=0) # default settings for SDAWG
    settings.update(update_settings)
    trigbyPXI, mode, sync, markeroption, Master, markerdelay = \
        settings['trigbyPXI'], settings['mode'], settings['sync'], settings['markeroption'], settings['Master'], settings['markerdelay']

    # 2. Choose Trigger Source:
    markerValue, trigio_direction = 0, 0
    if int(trigbyPXI) in range(8): extSource = 4000 + int(trigbyPXI) # BOTH Marking & Triggered by PXI.
    elif int(trigbyPXI)==-13: markerValue, extSource = 1, 4000 # Marking active-high via TrigIO-port on front panel, make PXI just a dummy.
    elif int(trigbyPXI)==-1: extSource, trigio_direction = 0, 1 # Triggered by TrigIO-port on front panel.

    channelist= [channel]
    if int(markeroption)==7: channelist.append(4)
    for channel in channelist:
        # 3. Pre-Settings:
        waveshape(module, channel, keysightSD1.SD_Waveshapes.AOU_AWG) # Arbitrary Shape for DAC
        sourcelevel(module, channel, ['Set', maxlevel, 0]) # Maximum amplitude in V
        module.AWGqueueConfig(channel, mode) # Operation-mode of the queue 
        configureExternalTrigger(module, channel, extSource, keysightSD1.SD_TriggerBehaviors.TRIGGER_FALL, sync) # Only FALL works: PXItrigger are active low signals

        # 4. Pre-Loading / Initiate waveform(s):
        waveform_id = int(channel) + 10 * module.getSlot() +  1000 * module.getChassis() # Unique ID: <Chassis___><Slot__><Channel_>
        sendWaveform(module, waveform_id, zeros([datasize]))

        # 5. Queue-up waveform(s):
        # NOTE: Follow orders AND Giving orders simultaneously: will produce an up-spike in marker-pulse.
        if Master: trigMode, markerMode = 0, keysightSD1.SD_MarkerModes.EVERY_CYCLE # Master / Commander / Default.
        else: trigMode, markerMode = keysightSD1.SD_TriggerModes.EXTTRIG, 0 # Follow orders from Master-Card.
        queueWaveform(module, channel, waveform_id, trigMode)
        
        # 6. Setting Trigger-IO port:
        trgIOmask = 1 # always open up trig-IO port
        triggerio(module, trigio_direction) # always output marker (hopefully)
        # trgIOmask = (abs(trigbyPXI) - trigbyPXI) / abs(trigbyPXI) / 2 # +ve: 0, -ve: 1
        # if trgIOmask==1: triggerio(module, not Master) # Trigger-IO ONLY (Card's Front 1st SMA-port) port-direction

        # 7. Configure marker(s):
        configureMarker(module, channel, [abs(trigbyPXI)], markerMode, int(trgIOmask), markerValue=markerValue, delay=markerdelay) # PXI and Trig-IO can output marker simultaneously!
        
    return module
def compose_DAC(module, channel, pulsedata, envelope=[], markeroption=0, update_settings={}):
    '''
    markeroption: 0 (disabled), 7 (PIN-Switch on MixerBox) (a.k.a. marker[1-4] for TKAWG)
    clearQ: MUST be used when ALL channels are FULLY assigned.
    '''
    # 1. Loading the settings:
    settings=dict(clearQ=0, Master=True, PINSW=False) # default settings for SDAWG
    settings.update(update_settings)
    clearQ, Master, PINSW = int(settings['clearQ']), settings['Master'], settings['PINSW']

    channelist= [channel]
    if int(markeroption)==7: channelist.append(4)
    for channel in channelist:
        waveform_id = channel + 10 * module.getSlot() +  1000 * module.getChassis() # Unique ID: <Chassis___><Slot__><Channel_>
        if (int(markeroption)==7) and (channel==4): 
            # Output MARKER through CH-4:
            mkr_array = zeros(len(pulsedata))
            if PINSW: # For DRIVING PIN-SWITCH: Following envelope.
                if len(envelope): mkr_array = abs(normalize_dipeak(envelope)) # always RISING
            else: # For TRIGGER PURPOSES: Making sure marker-width is finite & less than pulse-length.
                try: # pulse case
                    shrinkage = 3
                    first_rising_edge, last_falling_edge = where(ceil(abs(pulsedata-pulsedata[-1]))==1)[0][0], where(ceil(abs(pulsedata-pulsedata[-1]))==1)[0][-1]
                    last_falling_edge = first_rising_edge + int(ceil((last_falling_edge - first_rising_edge)/shrinkage))
                except: # CW case
                    first_rising_edge, last_falling_edge = 0, 300
                mkr_array[first_rising_edge : last_falling_edge] = 1
                print(Fore.YELLOW + "Output Trigger marker = 1/3 envelop: (%s - %s)" %(first_rising_edge, last_falling_edge))
            pulsedata = mkr_array

        if clearQ: 
            module.AWGstop(channel)
            module.AWGflush(channel) # Clear queue TO RESOLVE SYNC-ISSUE in FULL-4-CHANNELS OUTPUT
            print(Fore.CYAN + "Clearing CH%s's queue for good alignment of ALL 4 channels" %(channel))
        
        resendWaveform(module, waveform_id, pulsedata)
        
        if clearQ:
            # NOTE: TO RESOLVE SYNC-ISSUE in FULL-4-CHANNELS OUTPUT, step-2 are just repetitions of step-5 respectively from the "prepare_DAC".
            # 2. Queue-up waveform(s):
            if Master: trigMode, markerMode = 0, keysightSD1.SD_MarkerModes.EVERY_CYCLE # Master / Commander / Default.
            else: trigMode, markerMode = keysightSD1.SD_TriggerModes.EXTTRIG, 0 # Follow orders from Master-Card.
            queueWaveform(module, channel, waveform_id, trigMode)
            # PENDING: SEE IF BY ADDING "configureMarker" to Master the alignment would be solved?

    return module

# Dedicated for DC-sweep:
def output(module, state, channel=''):
    '''dummy channel to get along with the SRSDC.'''
    if state:
        for i in range(4): offset(module, i+1, 0) # zero ALL 4 channels
        ready(module, [1,2,3,4]) # open ALL 4 channels
        play(module)
        print(Fore.CYAN + "PLAYING ALL 4 channels")
    else: 
        stop(module, [1,2,3,4])
        print(Fore.CYAN + "STOPPING ALL 4 channels")
    return state
def sweep(module, dcvalue, channel=1, update_settings={}):
    '''DC amplitude in volts (–1.5 V to 1.5 V)
    '''
    try:
        # PENDING: includes sweeprate and pulsewidth, to be aligned with the YOKO.
        module.channelWaveShape(int(channel), keysightSD1.SD_Waveshapes.AOU_DC)
        status = module.channelAmplitude(int(channel), float(dcvalue))
        print(Fore.GREEN + "Sweeping DCZ Channel-%s at %s"%(channel,dcvalue))
    except(ValueError): print(Fore.CYAN + "DCZ is NOT sweeping Channel-%s"%(channel))
    except Exception as err: print("Error:\n%s"%err)
    return status


def close(module, which, reset=True, mode='DATABASE'):
    if reset:
        module.waveformFlush() # clear all old-waveforms in RAM
        for i in range(4): # close ALL 4 channels
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
#def test():
if __name__ == "__main__":
    # DAC_MATRIX = [[1,2,3,4],[1,2,3,4]] # WITHIN 100ns ALIGNMENT
    DAC_MATRIX = [[1,2],[1,2,3]] # PERFECTO ALIGNMENT
    DAC_LABEL = [3, 1]
    Master = [True, False]
    markeroption = [7, 0]
    Prep_settings = [dict(Master=True, trigbyPXI=2, markeroption=7), dict(Master=False, trigbyPXI=2)]
    marker = [7, 2]
    M = [None]*len(DAC_MATRIX)

    for i, channel_set in enumerate(DAC_MATRIX):
        print("channel_set for slot-%s: %s" %(i+1,channel_set))
        # INITIATION:
        M[i] = Initiate(DAC_LABEL[i], 'TEST')
        print(Fore.YELLOW + "Model: %s" %model(M[i])[1]['IDN'])
        clock(M[i], action=['Set', 'EFIXed',1e9])
        clear_waveform(M[i],'all')
        alloff(M[i], action=['Set',1])
        
        # Initiate PulseQ:
        dt = round(1/float(clock(M[i])[1]['SRATe'])/1e-9, 2)
        # print("Source: %s, Sampling rate: %s, dt: %s"%(clock(M[i])[1]['SOURce'], clock(M[i])[1]['SRATe'], dt))
        pulseq = pulser(dt, clock_multiples=1, score="ns=50000;")
        pulseq.song()
        # pulseq = pulser(dt, clock_multiples=1, score="ns=%s"%pulseq.totaltime)
        # pulseq.song()

        # PREPARATION:
        for ch in channel_set:
            prepare_DAC(M[i], int(ch), pulseq.totalpoints, update_settings=Prep_settings[i])
        # PRE-COMPOSITION:
        for ch in channel_set:
            # clearQ not needed at pre-compose:
            compose_DAC(M[i], int(ch), pulseq.music, [], markeroption[i])#, pulseq.envelope, 0, update_settings=dict(Master=Master[i], clearQ=int(bool(len(channel_set)==4))))
            print(Fore.BLUE + "Preparing %s data-points" %pulseq.totalpoints)
        alloff(M[i], action=['Set',0])
        ready(M[i])
        play(M[i])
    
    # Multiple WAVEs:
    for waveth,pulse_width in enumerate([1000,1700]):
        # stop(M[0]) # suggested by NCHU (YuHan)
        # stop(M[1]) # suggested by NCHU (YuHan)
        input("Any key to RUN %sth WAVE: "%(waveth+1))
        for i, channel_set in enumerate(DAC_MATRIX):
            print("Playing CH-%s for slot-%s" %(channel_set,i+1))
            for ch in channel_set:
                # RE-COMPOSITION:
                pulseq = pulser(dt, clock_multiples=1, score="ns=50000,mhz=I/-17/ro1i-17;FLAT/,%s,0.1;" %pulse_width)
                pulseq.song()
                compose_DAC(M[i], int(ch), pulseq.music, pulseq.envelope, marker[i], update_settings=dict(Master=Master[i], clearQ=int(bool(len(channel_set)==4))))
            ready(M[i])

    # print(Fore.CYAN + "Waveform-list: %s" %m2.waveformListLoad())
    # print(Fore.YELLOW + "PXI-%s: %s" %(1, m1.PXItriggerRead(1)))
    # print(Fore.YELLOW + "PXI-%s: %s" %(2, m1.PXItriggerRead(2)))

    # CLOSING:
    reset = bool(int(input("Reset (1/0): ")))
    for i, channel_set in enumerate(DAC_MATRIX):
        close(M[i], DAC_LABEL[i], reset, 'TEST')

    # Improvised DC test for Module 1-7:
    # m3 = Initiate(current=True, which=3, mode='TEST')
    # output(m3, 1)
    # dcvalues = [x*-0.01 for x in range(30)]
    # for val in dcvalues:
    #     input("Any key to output DC=%sV from AWG-3: " %val)
    #     sweep(m3, str(val), channel=2)
    # input("Any key to CLOSE AWG-3: ")
    # output(m3, 0)
    # close(m3, 3, True, 'TEST')

    #return

#test()