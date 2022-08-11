# Communicating with Benchtop DSA8300 (Tektronix Sampling Scope)
from colorama import init, Fore, Back
init(autoreset=True) #to convert termcolor to wins color

from os.path import basename as bs
mdlname = bs(__file__).split('.')[0] # module's name e.g. PSG

import visa
from pyqum.instrument.logger import address, set_status, status_code, debug
from pyqum.instrument.logger import translate_scpi as Attribute
from numpy import array
import array as arr

from pyqum.instrument.toolbox import squarewave
from time import sleep
debugger = debug(mdlname)

# INITIALIZATION
def Initiate():
    ad = address()
    rs = ad.lookup(mdlname) # Instrument's Address
    rm = visa.ResourceManager()
    try:
        bench = rm.open_resource(rs) #establishing connection using GPIB# with the machine
        stat = bench.write('*ESR?') #basic query
        bench.read_termination = '\n' #omit termination tag from output 
        bench.timeout = 150000 #set timeout in ms
        set_status(mdlname, dict(state='connected'))
        print(Fore.GREEN + "%s's connection Initialized: %s" % (mdlname, str(stat[1])[-7:]))
    except: 
        set_status(mdlname, dict(state='DISCONNECTED'))
        print(Fore.RED + "%s's connection NOT FOUND" % mdlname)
        bench = "disconnected"
    return bench

@Attribute
def model(bench, action=['Get', '']):
    SCPIcore = '*IDN'  #inquiring machine identity: "who r u?"
    return mdlname, bench, SCPIcore, action
@Attribute
def ready(bench, action=['Get', '']):
    SCPIcore = '*OPC'  #inquiring machine: "r u ready?"
    return mdlname, bench, SCPIcore, action

@Attribute
def clock(bench, action=['Get'] + 10 * ['']):
    '''
    Source:
    INTernal - Clock signal is generated internally and the reference frequency is derived from the internal oscillator. 
    EFIXed – Clock is generated internally and the reference frequency is derived from a ﬁxed 10MHz reference supplied at the Reference-In connector. 
    EVARiable – Clock is generated internally and the reference frequency is derived from a variable reference supplied at the Reference-In connector. 
    EXTernal – Clock signal supplied by the Clock In connector. The reference frequency is deactivated. 
    *RST sets this to INT.
    Rate:
    Range: 298 S/s to 2.5 G/s (option-25), 298 S/s to 5 G/s (option-50)
    *RST sets this to the maximum value.
    '''
    SCPIcore = 'CLOCk:SOURce;SRATe'
    return mdlname, bench, SCPIcore, action

@Attribute
def waveformlist(bench, action=['Get']):
    '''
    Most Recent, A List of, Size of Waveform-list (Query ONLY)
    '''
    SCPIcore = 'WLISt:LAST;LIST;SIZE'
    action += 10 * [''] # for multiple parameters
    return mdlname, bench, SCPIcore, action
@Attribute
def waveformpick(bench, action=['Get']):
    '''
    This command returns the waveform name from the waveform list at the position speciﬁed by the index value. (Query ONLY)
    '''
    SCPIcore = 'WLISt:NAME'
    action += 10 * [''] # for multiple parameters
    return mdlname, bench, SCPIcore, action

@Attribute
def outputpath(bench, channel, action=['Get'] + 10 * ['']):
    '''This command sets or returns the output path of the speciﬁed channel.
    Path:  DCHB (DC High Bandwidth), DCHV (DC High Voltage), ACD (AC Direct), ACAM (AC Ampliﬁed)
    '''
    SCPIcore = 'OUTPUT%s:PATH' %channel
    return mdlname, bench, SCPIcore, action
@Attribute
def output(bench, channel, action=['Get'] + 10 * ['']):
    '''This command sets or returns the output state of the speciﬁed channel.
    '''
    SCPIcore = 'OUTPUT%s:STATE' %channel
    return mdlname, bench, SCPIcore, action
@Attribute
def alloff(bench, action=['Get'] + 10 * ['']):
    '''This command sets or returns the state (enabled or disabled) of the 'All Outputs Off' control.
    '''
    SCPIcore = 'OUTPUT:OFF'
    return mdlname, bench, SCPIcore, action
@Attribute
def sourcelevel(bench, channel, action=['Get'] + 10 * ['']):
    '''This command sets or returns the amplitude and offset for the waveform associated with the speciﬁed channel. 
    '''
    SCPIcore = 'SOURCE%s:VOLTAGE:LEVEL:IMMEDIATE:AMPLITUDE;OFFSET' %channel
    return mdlname, bench, SCPIcore, action
@Attribute
def sourceresolution(bench, channel, action=['Get'] + 10 * ['']):
    '''This command sets or returns the DAC resolution. 
        16(12) indicates 16 bit DAC Resolution + 0(4) Marker bits. 
    '''
    SCPIcore = 'SOURCE%s:DAC:RESOLUTION' %channel
    return mdlname, bench, SCPIcore, action
@Attribute
def markerdelay(bench, channel, marker, action=['Get'] + 10 * ['']):
    '''This command sets or returns the delay for the speciﬁed marker of the speciﬁed channel. 
        Marker delay is independent for each channel. Range: –3 ns to 3 ns 
        *RST sets all channel marker delays to 0.
    '''
    SCPIcore = 'SOURCE%s:MARKER%s:DELAY' %(channel,marker)
    return mdlname, bench, SCPIcore, action
@Attribute
def runmode(bench, channel, action=['Get'] + 10 * ['']):
    '''This command sets or returns the run-mode of the speciﬁed channel:
        [SOURce[n]:]RMODe {CONTinuous|TRIGgered|TCONtinuous|GATed}
    '''
    SCPIcore = 'SOURCE%s:RMODE' %channel
    return mdlname, bench, SCPIcore, action
@Attribute
def runstate(bench, action=['Get'] + 10 * ['']):
    '''This command returns the run-state of the AWG. (Query ONLY)
        0 indicates that the AWG has stopped. 
        1 indicates that the AWG is waiting for trigger. 
        2 indicates that the AWG is running.
    '''
    SCPIcore = 'AWGCONTROL:RSTATE'
    return mdlname, bench, SCPIcore, action

@Attribute
def testscpi(bench, action=['Get', '']):
    '''TEST SCPI CODE'''
    # SCPIcore = 'WLISt:LIST'
    SCPIcore = 'OUTPUT1:STATE'
    return mdlname, bench, SCPIcore, action

# Handling Waveforms:
def initwaveform(bench,name,size):
    '''Initialize waveform with its name and length'''
    status = bench.write('WLIST:WAVEFORM:NEW "%s",%s,REAL' %(name,size))
    return status
def create_waveform(bench,name,data,startindex=0):
    '''This command has a limit of 999,999,999 bytes of data (~49ms of single playtime per waveform given max sampling rate). 
        The IEEE 488.2 limits that the largest read or write that may occur in a single command is 999,999,999 bytes. 
        Because of the size limitation, it is suggested that the user make use of the starting index (and size for querying) to append data in multiple commands/queries. 
    '''
    try: 
        # bench.write_binary_values('WLIST:WAVEFORM:DATA "%s",%s,%s,'%(name,startindex,size), data, datatype='d', is_big_endian=False) # Old way
        # Prepare the data block from data array:
        wavebytes = arr.array('f', array(data).astype('float32')).tobytes()  # use 32-bit or 4-Byte floating numbers
        # Assemble SCPI command:
        bytesize = len(wavebytes)
        command = ('WLISt:WAVeform:DATA "{}",{},{},'.format(name,startindex,bytesize//4)).encode('UTF-8')
        header = ('#' + str(len(str(bytesize))) + str(bytesize)).encode('UTF-8')
        # Send to machine:
        status = bench.write_raw(command + header + wavebytes)
    except: 
        # raise 
        print("Check waveform again?")
    # print(status)
    return status
def create_markers(bench,name,channel,marker,data,startindex=0):
    '''This command sets or returns the waveform marker data.
        This command has a limit of 999,999,999 bytes of data. 
        The marker arrays must contain only 1's and 0's.
        Each marker data occupies one bit. Four most signiﬁcant bits of each byte are used for markers. 
        Bit 7 for marker 1 and bit 6 for marker 2, bit 5 for marker 3, and bit 4 for marker 4.
        You will have to use bit masks to obtain the actual value. 
        When used on a waveform with n data points, you get only n bytes, each byte having values for both markers. 
    '''
    try: 
        # Adjust DAC resolution to accomadate more markers:
        sourceresolution(bench, channel, action=['Set',16-int(marker)])
        # Masking marker: (PENDING: multiple markers)
        data = array(data) * 2**(8-int(marker)) # Bit 7 for marker 1, bit 6 for marker 2, bit 5 for marker 3, bit 4 for marker 4.
        # Prepare the data block from data array:
        markerbytes = arr.array('B', data.astype('uint8')).tobytes()  # use 8-bit or 1-Byte integer numbers
        # Assemble SCPI command:
        bytesize = len(markerbytes)
        command = ('WLIST:WAVEFORM:MARKER:DATA "{}",{},{},'.format(name,startindex,bytesize)).encode('UTF-8')
        header = ('#' + str(len(str(bytesize))) + str(bytesize)).encode('UTF-8')
        # Send to machine:
        status = bench.write_raw(command + header + markerbytes)
    except: 
        # raise 
        print("Check marker again?")
    # print(command + header + markerbytes)
    return status
def assign_waveform(bench,name,channel):
    status = bench.write('SOURCE%s:CASSET:WAVEFORM "%s"' %(channel,name))
    return status
def normalize_waveform(bench,name):
    '''This command normalizes a waveform in the waveform list.
    '''
    bench.write('WLIST:WAVEFORM:NORMALIZE "%s",ZREFerence' %(name))
    status = bench.query('*OPC?')
    return status
def clear_waveform(bench,name):
    if name.lower() == 'all':
        status = bench.write('WLIST:WAVEFORM:DELETE ALL')
    else: status = bench.write('WLIST:WAVEFORM:DELETE "%s"' %name)
    return status

def play(bench):
    try:
        status = bench.write('AWGCONTROL:RUN:IMMEDIATE') # Playing
        set_status(mdlname, dict(play='yes'))
    except: set_status(mdlname, dict(play='error'))
    return status
def stop(bench):
    try:
        status = bench.write('AWGCONTROL:STOP:IMMEDIATE') # Stop Playing
        set_status(mdlname, dict(play='no'))
    except: set_status(mdlname, dict(play='error'))
    return status

def close(bench, reset=True):
    if reset:
        bench.write('*RST') # reset to factory setting
        set_status(mdlname, dict(config='reset'))
    else: set_status(mdlname, dict(config='previous'))
    try:
        # acquire(bench, action=['Set','OFF','']) # STOP ACQUISITION
        bench.close() #None means Success?
        status = "Success"
    except: status = "Error"
    set_status(mdlname, dict(state='disconnected'))
    print(Back.WHITE + Fore.BLACK + "%s's connection Closed" %(mdlname))
    return status

# Composite functions for directives:
def prepare_DAC(bench, channel, datasize, maxlevel=0.75):
    initwaveform(bench, "Waveform-%s"%channel, datasize)
    normalize_waveform(bench, "Waveform-%s"%channel)
    runmode(bench, channel, action=['Set','CONT'])
    sourcelevel(bench, channel, action=['Set',maxlevel,0])
    outputpath(bench, channel, action=['Set','DCHB'])
    return bench
def compose_DAC(bench, channel, pulsedata, marker=0, markersize=0):
    # MUST Create waveform before markers:
    create_waveform(bench, "Waveform-%s"%channel, pulsedata)
    if marker-1 in range(4): # only 1-4 is valid
        create_markers(bench, "Waveform-%s"%channel, channel, marker, array([1]*markersize+[0]*(len(pulsedata)-markersize)))
    else:
        sourceresolution(bench, channel, action=['Set',16])
    assign_waveform(bench, "Waveform-%s"%channel, channel)
    ready(bench)
    output(bench, channel, action=['Set','ON'])
    return bench

# Test Zone
def test(detail=True):
    s = Initiate()
    if s is "disconnected":
        pass
    else:
        if debug(mdlname, detail):
            print(Fore.RED + "Detailed Test:")
            model(s)
            clock(s)
            waveformlist(s)
            waveformpick(s, action=['Get','0'])

            # To be put in directives:
            level = [0.7, 0.2]
            ch = [1,2,3,4]
            clock(s, action=['Set', 'EFIXed',2.5e9])
            clear_waveform(s,'all')
            alloff(s, action=['Set',1])

            # Prepare all channels:
            for i in range(4):
                prepare_DAC(s, ch[i], 20000)
            # Compose each waveforms into respective channels:
            compose_DAC(s, ch[0], array(squarewave(8000, 100, 0, level[0], dt=0.4, clock_multiples=1)), 1, 200)
            compose_DAC(s, ch[1], array(squarewave(8000, 0, 0, level[0], dt=0.4, clock_multiples=1)))
            compose_DAC(s, ch[2], array(squarewave(8000, 100, 0, level[1], dt=0.4, clock_multiples=1)), 1, 200)
            compose_DAC(s, ch[3], array(squarewave(8000, 0, 0, level[1], dt=0.4, clock_multiples=1)))
            
            alloff(s, action=['Set',0])
            ready(s)
            print("Play: %s" %str(play(s)))

            # Changing waveform on the fly:
            # sleep(7)
            # compose_DAC(s, ch[0], array(squarewave(8000, 2000, 0, level, dt=0.4, clock_multiples=1)), 1, 200)
            # compose_DAC(s, ch[1], array(squarewave(8000, 0, 0, level, dt=0.4, clock_multiples=1)))
            # sleep(7)
            # compose_DAC(s, ch[0], array(squarewave(8000, 3000, 0, level, dt=0.4, clock_multiples=1)), 1, 200)
            # compose_DAC(s, ch[1], array(squarewave(8000, 0, 0, level, dt=0.4, clock_multiples=1)))
            # sleep(7)
            # compose_DAC(s, ch[0], array(squarewave(8000, 5000, 0, level, dt=0.4, clock_multiples=1)), 1, 200)
            # compose_DAC(s, ch[1], array(squarewave(8000, 0, 0, level, dt=0.4, clock_multiples=1)))

            ch = 3
            runmode(s, ch)
            output(s, ch)
            sourcelevel(s, ch)
            sourceresolution(s, ch)
            runstate(s)

        else: print(Fore.RED + "Basic IO Test")
    if not bool(input("Press ENTER (OTHER KEY) to (skip) reset: ")):
        state = True
    else: state = False
    close(s, reset=state)
    return

# test()