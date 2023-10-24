# Type
from numpy import nan, isnan 
# Math
from numpy import pi, radians

import pulse_signal.common_Mathfunc as cpf
from pulse_signal.pulse import Pulse


# try to put this function into waveform.py but with circular import error
# give waveform parametars like sigma, amplitude,...
def give_waveformInfo(beat,width,height)->dict:
    paraList = []
    for p in beat.split(',')[0].split('/')[1:]:
        if p == '':
            paraList.append( nan )
        else:
            paraList.append( float(p) )     
    # waveformParas -> flat : nan , drag : 4,-0.8,0

    waveform = beat.split('/')[0]
    match waveform:
        case "flat":
            pulse_func = cpf.constFunc
            func_paras = [height]
            carrierPhase = 0
        case "gauss":
            pulse_func = cpf.GaussianFamily
            if isnan(paraList[0]): sfactor = 4
            else: sfactor = paraList[0]
            carrierPhase = 0
            func_paras = [height, width/sfactor, width/2, 0]

        case "erfgauss" | "erf" | "erfg":
            pulse_func = cpf.GaussianFamily
            if isnan(paraList[0]): sfactor = 4
            else: sfactor = paraList[0]
            carrierPhase = 0
            
            # amp_erf = cpf.ErfAmplifier(height,width,width/sfactor)
            shift = cpf.ErfShifter(width,width/sfactor)

            func_paras = [height, width/sfactor, width/2, shift]

        case "hermite":
            pulse_func = cpf.HermiteFunc
            if len(paraList)==1:
                alpha = 2 # only for RB where tg = 4*sigma so alpha = 2
                beta = 4

            else:
                if isnan(paraList[0]): alpha = 2
                else: alpha = paraList[0]
                if isnan(paraList[1]): beta = 4
                else: beta = paraList[1]
            carrierPhase = 0
            func_paras = [height, alpha, beta, width/2]
        
        case "tangential" | "tan":
            print("********* Func is Tan with Amp = %f ********"%height)
            pulse_func = cpf.TangentialFunc
            if len(paraList)==1:
                sfactor = 4
            else:
                if isnan(paraList[0]): sfactor = 4
                else: sfactor = paraList[0]
            carrierPhase = 0
            func_paras = [height, width/sfactor, width/2]
        


        case "gaussup":
            pulse_func = cpf.GaussianFamily
            if isnan(paraList[0]): sfactor = 4
            else: sfactor = paraList[0]
            carrierPhase = 0
            func_paras = [height, width*2/sfactor, width,0]

        case "gaussdn":
            pulse_func = cpf.GaussianFamily
            if isnan(paraList[0]): sfactor = 4
            else: sfactor = paraList[0]
            carrierPhase = 0
            func_paras = [height, width*2/sfactor, 0, 0]

        case "drage":   # waveform with ErfGaussian
            pulse_func = cpf.DRAGFunc
            if len(paraList)==1:
                sfactor = 4
                dRatio = 0.361716
                rotAxis = 0

            else:
                if isnan(paraList[0]): sfactor = 4
                else: sfactor = paraList[0]
                if isnan(paraList[1]): dRatio = 0.361716
                else: dRatio = paraList[1]
                if isnan(paraList[2]): rotAxis = 0
                else: rotAxis = radians(paraList[2])
            carrierPhase = rotAxis
            #amp_erf = cpf.ErfAmplifier(height,width,width/sfactor)
            shift = cpf.ErfShifter(width,width/sfactor)
            func_paras = [height, width/sfactor, width/2, shift, dRatio ]
        
        case "dragh":   # waveform with hermite
            pulse_func = cpf.DRAGFunc_Hermite
            if len(paraList)==1:
                alpha = 4
                beta = 4
                dRatio = 0.5
                rotAxis = 0
            else:
                if isnan(paraList[1]): alpha = 4
                else: alpha = paraList[1]
                if isnan(paraList[2]): beta = 4
                else: beta = paraList[2]
                if isnan(paraList[3]): dRatio = 0.5
                else: dRatio = paraList[3]
                if isnan(paraList[4]): rotAxis = 0
                else: rotAxis = radians(paraList[4])

            carrierPhase = rotAxis
            func_paras = [height, alpha, beta, width/2, dRatio ]

        case "drag":
            pulse_func = cpf.DRAGFunc
            if len(paraList)==1:
                sfactor = 4
                dRatio = 0
                rotAxis = 0
            else:
                if isnan(paraList[0]): sfactor = 4
                else: sfactor = paraList[0]
                if isnan(paraList[1]): dRatio = 0
                else: dRatio = paraList[1]
                if isnan(paraList[2]): rotAxis = 0
                else: rotAxis = radians(paraList[2])
            carrierPhase = rotAxis
            func_paras = [height, width/sfactor, width/2, 0, dRatio ]

        case "lin":
            pulse_func = cpf.linearFunc
            if isnan(paraList[0]): start = 0
            else: start = paraList[0]
            if isnan(paraList[1]): end = 0
            else: end = paraList[1]
            carrierPhase = 0
            slope = (start-end)/width
            func_paras = [slope, start]

        case "eerp":    # waveform with Error edge rectangular pulse
            pulse_func = cpf.EERP
            if len(paraList) == 1:
                sfactor = 4
                edgeWidth = 10
                peakMultiplier = 0
            else:
                if isnan(paraList[0]): sfactor = 4
                else: sfactor = paraList[0]
                if isnan(paraList[1]): edgeWidth = 10
                else: edgeWidth = paraList[1]
                if isnan(paraList[2]): peakMultiplier = 0
                else: peakMultiplier = paraList[2]
            carrierPhase = 0
            func_paras = [height, edgeWidth/2, edgeWidth/sfactor, width, 0]

        case "gerp":
            pulse_func = cpf.GERPFunc
            if len(paraList)==1:
                sfactor = 4
                edgeWidth = 30
                peakMultiplier = 0
            else:
                if isnan(paraList[0]): sfactor = 4
                else: sfactor = paraList[0]
                if isnan(paraList[1]): edgeWidth = 30
                else: edgeWidth = paraList[1]
                if isnan(paraList[2]): peakMultiplier = 0
                else: peakMultiplier = paraList[2]
            carrierPhase = 0
            func_paras = [height, width, 0, edgeWidth, edgeWidth*2/sfactor]
        case _:
            pulse_func = cpf.constFunc
            func_paras = [height]
            carrierPhase = 0

    new_pulse = Pulse()
    new_pulse.duration = width
    new_pulse.envelopeFunc = pulse_func
    new_pulse.carrierPhase = carrierPhase
    new_pulse.parameters = func_paras
    
    return new_pulse