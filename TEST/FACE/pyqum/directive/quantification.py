# Loading Basics
from colorama import init, Back, Fore
init(autoreset=True) #to convert termcolor to wins color
from os.path import basename as bs
myname = bs(__file__).split('.')[0] # This py-script's name
import sys, struct

from importlib import import_module as im
from flask import Flask, request, render_template, Response, redirect, Blueprint, jsonify, session, send_from_directory, abort, g
from pyqum.instrument.logger import address, get_status, set_status, set_mat, set_csv, clocker, mac_for_ip, lisqueue, lisjob, measurement, qout, jobsearch, get_json_measurementinfo, set_mat_analysis
from pyqum.instrument.toolbox import cdatasearch, gotocdata, waveform
from numpy import array, unwrap, mean, trunc, sqrt, zeros, ones, shape, arctan2, int64, isnan, abs, empty, ndarray, moveaxis, reshape, expand_dims, logical_and, nan, arange, exp, amax, amin, diag, concatenate, append, angle, argmax, linspace, arctan, tan
from numpy.fft import fft, fftfreq
from scipy.odr import *

# Json to Javascrpt
import json

# Error handling
from contextlib import suppress

# Scientific
from scipy import constants as cnst
from scipy.optimize import curve_fit
from scipy.stats import linregress

#from si_prefix import si_format, si_parse
from numpy import cos, sin, pi, polyfit, poly1d, polyval, array, roots, isreal, sqrt, mean, std, histogram, average, newaxis, float64, any, var, transpose

# Load instruments
# Please Delete this line in another branch (to: @Jackie)
from pyqum.directive import calibrate 
from pyqum.mission import get_measurementObject

# Fitting
from collections import defaultdict
from pyqum.directive.tools.circuit import notch_port
from pyqum.directive.tools.utilities import plotting, save_load, Watt2dBm, dBm2Watt
from pyqum.directive.tools.circlefit import circlefit
from pyqum.directive.tools.calibration import calibration
from pyqum.directive.tools.not_sin import *
from sklearn.metrics import r2_score
import pandas as pd
# Save file
from scipy.io import savemat
# fidelity
from matplotlib.patches import Ellipse
from matplotlib import transforms
from sklearn.cluster import KMeans
from sklearn.svm import SVC
from numpy import stack, unique, meshgrid
import pickle
from state_distinguishability.iq_kmean import *

class ExtendMeasurement ():
	def __init__( self, measurementObj, *args,**kwargs ):
		self.measurementObj = measurementObj
		self.independentVars = {}
		# Key and index
		self.xAxisKey = None
		self.yAxisKey = None

		self.varsInd = []
		self.axisInd = []
		self.aveAxisKey = None
		self.averageInd = []
		self.oneShotAxisKey = None
		self.oneShotClusterCenters = []
		self.innerRepeatKeys = []
		# Selected Data
		self.rawData = {}
		# Initialize
		self._init_rawData()

		# Integrate R-Parameters back into C-Order:
		if "R-JSON" in self.measurementObj.perimeter:
			RJSON = json.loads(self.measurementObj.perimeter['R-JSON'].replace("'",'"'))

			# Recombine Buffer back into C-Order:
			if self.measurementObj.perimeter['READOUTYPE'] == 'one-shot': bufferkey = 'RECORD-SUM'
			else: bufferkey = 'RECORD_TIME_NS'

			# Extend C-Structure with R-Parameters & Buffer keys:
			self.measurementObj.corder['C-Structure'] = self.measurementObj.corder['C-Structure'] + [k for k in RJSON.keys() if ">" not in k] + [bufferkey] # Fixed-Structure + R-Structure + Buffer

		C_Shape = []
		for k in measurementObj.corder["C-Structure"] :
			# Get wavefrom object from c-order
			try:
				varWaveform = waveform( measurementObj.corder[k] )
			except(KeyError):
				varWaveform = waveform('opt,')
			# Get array from Waveform object
			self.independentVars[k]=array(varWaveform.data)
			# Get C-Shape from Waveform object
			C_Shape.append( varWaveform.count*varWaveform.inner_repeat  )
			if varWaveform.inner_repeat != 1:
				self.innerRepeatKeys.append( k )

		# Append datadensity to C-Shape (list) and Measurement.corder["C-Structure"] (list)
		measurementObj.corder["C-Structure"].append("datadensity")
		C_Shape.append( measurementObj.datadensity )
		# Add C-Shape (list) to Measurement.corder (Dict)
		self.measurementObj.corder["C_Shape"] = C_Shape
		print("Init", self.measurementObj.corder)

		# Optimize (developing)
		'''
		self.optCShpae = C_Shape
		self.optCStructure = measurementObj.corder["C-Structure"]
		for s, k in zip(C_Shape,measurementObj.corder["C-Structure"]) :
			if s == 1:
				self.optCShpae.remove(s)
				self.optCStructure.remove(k)
		'''


	def _init_rawData( self, yAxisLen=0, xAxisLen=0 ):
		self.rawData = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}

	def reshape_Data ( self, varsInd, axisInd=[], aveInfo=None ):
		# Data dimension should <= 3
		print("Reshape Data")

		# Get average parameters
		if len(aveInfo["axisIndex"]) != 0:
			self.aveAxisKey = self.measurementObj.corder["C-Structure"][aveInfo["axisIndex"][0]]
			self.averageInd = aveInfo["aveRange"]
		else:
			self.aveAxisKey = None

		# Get one shot parameters	
		if len(aveInfo["oneShotAxisIndex"]) != 0:
			self.oneShotAxisKey = self.measurementObj.corder["C-Structure"][aveInfo["oneShotAxisIndex"][0]]
			self.oneShotClusterCenters = aveInfo["oneShotCenters"]
			print(f"Set center point {self.oneShotClusterCenters}")
		else:
			self.oneShotAxisKey = None


		cShape = self.measurementObj.corder["C_Shape"]
		self.xAxisKey = self.measurementObj.corder["C-Structure"][axisInd[0]]
		# Get axis key from C-order
		if len(axisInd)== 2:
			self.yAxisKey = self.measurementObj.corder["C-Structure"][axisInd[1]]
		else:
			self.yAxisKey = None

		self.varsInd = varsInd.copy()
		self.axisInd = axisInd.copy()


		self.measurementObj.loadata()
		data = self.measurementObj.selectedata
		data = reshape( data, tuple(cShape) )
		varsInd.append(1) # Temporary for connect with old data type

		# Make array of key to move axis of data
		if self.yAxisKey == None:
			moveAxisKey = ["datadensity", self.xAxisKey]
		else:
			moveAxisKey = ["datadensity", self.yAxisKey, self.xAxisKey]

		# Add ave axis
		if self.aveAxisKey != None:
			moveAxisKey = moveAxisKey +[self.aveAxisKey]

		# Add one shot axis
		if self.oneShotAxisKey != None:
			moveAxisKey = moveAxisKey +[self.oneShotAxisKey]

		selectValInd = []
		includeAxisInd = []
		for i, k in enumerate(self.measurementObj.corder["C-Structure"]):
			if k not in moveAxisKey: # Get position for the axis only need one value
				selectValInd.append(varsInd[i])

			else: # Get arranged indice of the axis for analysis
				includeAxisInd.append(i)

		includeAxisInd = []
		newAxisPosition = []
		for i, k in enumerate(moveAxisKey):
			includeAxisInd.append(self.measurementObj.corder["C-Structure"].index(k) )
			newAxisPosition.append(-len(moveAxisKey)+i)
		data = moveaxis( data, includeAxisInd, newAxisPosition )

		# Remove one value dimension
		for vi in selectValInd:
			data = data[vi]

		
		if self.aveAxisKey != None: # Get average from independentVars aveAxisKey
			data = mean(data, axis=len(data.shape)-1, where=self.array_mask())



		
		# Get data to analysis
		self.rawData = { 
			"x": self.independentVars[self.xAxisKey], 
			"iqSignal": data[0]+1j*data[1],
		}
		if self.oneShotAxisKey != None: #Get population from given center
			self.rawData["iqSignal"] = get_population(array(self.oneShotClusterCenters), self.rawData["iqSignal"])
		# To 3 dimension
		if self.rawData["iqSignal"].ndim == 1:
			self.rawData["iqSignal"] = expand_dims(self.rawData["iqSignal"],axis=0)

	def array_mask( self ) :
		indexArray = arange(len(self.independentVars[self.aveAxisKey]))
		mask = logical_and(indexArray>=self.averageInd[0], indexArray<=self.averageInd[1]) 
		return mask


	def get_htmlInfo( self ):
		hiddenKeys = ["datadensity"]
		htmlInfo = []
		for i, (k, l) in enumerate(zip(self.measurementObj.corder["C-Structure"],self.measurementObj.corder["C_Shape"])):
			if k not in hiddenKeys:
				info = {
					"name": k,
					"length": l,
					"structurePosition": i,
					"c_order": self.measurementObj.corder[k]
				}
				htmlInfo.append(info)
		return htmlInfo

class QEstimation():

	def __init__( self, quantificationObj, *args,**kwargs ):

		self.quantificationObj = quantificationObj
		# Key and index
		self.powerKey = "Power"
		
		# Fit
		self.fitCurve = {}
		self.baseline = {}
		self.correctedIQData = {}
		self.fitResult = {}

		self._fitParameters = None
		self._init_fitResult()
		
		self._init_fitCurve()
		self._init_baselineCorrection()



	def _init_fitResult( self, yAxisLen=0 ):
		nanArray = empty([yAxisLen])
		nanArray.fill( nan )

		resultKeys = ["Qi_dia_corr","Qi_no_corr","absQc","Qc_dia_corr","Ql","fr","theta0","phi0"]
		errorKeys = ["phi0_err", "Ql_err", "absQc_err", "fr_err","chi_square","Qi_no_corr_err","Qi_dia_corr_err"]
		extendResultKeys = ["power_corr", "single_photon_limit", "photons_in_resonator"]
		results ={}
		errors ={}
		extendResults ={}
		for rk in resultKeys:
			results[rk] = nanArray.copy()
		for ek in errorKeys:
			errors[ek] = nanArray.copy()
		for erk in extendResultKeys:
			extendResults[erk] = nanArray.copy()

		self.fitResult={
			"results": results,
			"errors": errors,
			"extendResults": extendResults,
		}

	def _init_fitCurve( self, yAxisLen=0, xAxisLen=0 ):
		self.fitCurve = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}
	def _init_baselineCorrection( self, yAxisLen=0, xAxisLen=0  ):
		self.baseline = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}
		self.correctedIQData = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}
	@property
	def fitParameters(self):
		return self._fitParameters

	@fitParameters.setter
	def fitParameters(self, fitParameters=None):
		if fitParameters == None:
			fitParameters={
				"interval": {
					"start": 5,
					"end": 8
				},
				"baseline":{
					"correction": False,
					"smoothness": 1e9,
					"asymmetry": 0.995,
				},				
				"gain":0,
			}
		else:
			fitRange = [float(k) for k in fitParameters["interval"]["input"].split(",")]
			fitParameters["interval"]["start"] = fitRange[0]
			fitParameters["interval"]["end"] = fitRange[1]
			fitParameters["baseline"]["smoothness"] = float(fitParameters["baseline"]["smoothness"])
			fitParameters["baseline"]["asymmetry"] = float(fitParameters["baseline"]["asymmetry"])
			fitParameters["gain"] = float(fitParameters["gain"])
		self._fitParameters = fitParameters





	def do_analysis( self, freqUnit = "GHz" ):

		qObj = self.quantificationObj
		xAxisLen = qObj.rawData["x"].shape[0]


		freqUnitConvertor = 1 # Convert to Hz
		if freqUnit == "GHz":
			freqUnitConvertor = 1e9

		fitRange = ( self.fitParameters["interval"]["start"]*freqUnitConvertor, self.fitParameters["interval"]["end"]*freqUnitConvertor )

		# Get 1D or 2D data to self.rawData
		if qObj.yAxisKey == None:
			yAxisLen = 1
		else:
			yAxisLen = qObj.independentVars[qObj.yAxisKey].shape[0]

		self._init_fitCurve(yAxisLen=yAxisLen,xAxisLen=xAxisLen)
		self._init_baselineCorrection(yAxisLen=yAxisLen,xAxisLen=xAxisLen)
		self._init_fitResult(yAxisLen=yAxisLen)



		myResonator = notch_port()
		# Creat notch port list
		for i in range(yAxisLen):
			# Fit baseline
			if self.fitParameters["baseline"]["correction"] == True :
				fittedBaseline = myResonator.fit_baseline_amp( qObj.rawData["iqSignal"][i], self.fitParameters["baseline"]["smoothness"], self.fitParameters["baseline"]["asymmetry"],niter=1)
				correctedIQ = qObj.rawData["iqSignal"][i]/fittedBaseline
				# Save Corrected IQ Data
				self.correctedIQData["iqSignal"][i] = correctedIQ
				# Save baseline
				self.baseline["iqSignal"][i] = fittedBaseline
			else: 
				self._init_baselineCorrection()
				correctedIQ = qObj.rawData["iqSignal"][i]
			# Add data
			myResonator.add_data(qObj.rawData["x"]*freqUnitConvertor, correctedIQ)
			# Fit
			try:
				myResonator.autofit(fcrop=fitRange)
				fitSuccess = True
				print("Good fitting")

			except:
				fitSuccess = False
				print("Bad fitting")


			if fitSuccess:

				for k in self.fitResult["results"].keys():
					self.fitResult["results"][k][i] = myResonator.fitresults[k]

				for k in self.fitResult["errors"].keys():
					self.fitResult["errors"][k][i] = myResonator.fitresults[k]


				self.fitResult["extendResults"]["single_photon_limit"][i] = myResonator.get_single_photon_limit(unit='dBm',diacorr=True)

				if qObj.yAxisKey == self.powerKey:
					powerIndex = i
				else:
					powerAxisIndex = qObj.measurementObj.corder["C-Structure"].index(self.powerKey)
					powerIndex = qObj.varsInd[powerAxisIndex]

				self.fitResult["extendResults"]["power_corr"][i] = qObj.independentVars["Power"][powerIndex]+self.fitParameters["gain"]
				self.fitResult["extendResults"]["photons_in_resonator"][i] = myResonator.get_photons_in_resonator(self.fitResult["extendResults"]["power_corr"][i],unit='dBm',diacorr=True)
				
				# Set x-axis (frequency) of fit curve 
				
				self.fitCurve["x"] = qObj.rawData["x"]
				self.fitCurve["iqSignal"][i] = myResonator.z_data_sim
				# Set x-axis (frequency) of baseline and corrected data 
				if self.fitParameters["baseline"]["correction"] == True :
					self.baseline["x"] = qObj.rawData["x"]
					self.correctedIQData["x"] = qObj.rawData["x"]
				else: 
					self._init_baselineCorrection()

class PopulationDistribution():

	def __init__( self, quantificationObj, *args,**kwargs ):

		self.quantificationObj = quantificationObj
		# Key and index
		# Accumulated data for fit straight line
		self.accData={
			"raw":[],
			"shifted":[],
			"projected":[],
		}

		# Projection line
		self.projectionLine = {
			"data":[],
			"parameter":[],
		}


		# Histogram
		self.distribution={
			"x":[],
			"count":[],
			"fitted":[]
		}

		self._fitParameters = None
		# Fit
		self.real, self.imag = [],[]
		self.label_list= ["gnd","exc"]
		self.probability = []
		self.bleed = 10**-4

	def _init_fitResult( self, yAxisLen=0 ):
		nanArray = empty([yAxisLen])
		nanArray.fill( nan )

		results ={}
		errors ={}
		for rk in self.resultKeys:
			results[rk] = nanArray.copy()
		for ek in self.errorKeys:
			errors[ek] = nanArray.copy()


		self.fitResult={
			"results": results,
			"errors": errors,
		}

	def _init_fitCurve( self, yAxisLen=0, xAxisLen=0 ):
		self.fitCurve = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}

	def accumulate_data( self, accumulationIndex ):
		
		qObj = self.quantificationObj

		accData= array([])
		for accInd in accumulationIndex:
			accData= append(accData,qObj.rawData["iqSignal"][accInd])

		meanPoint = mean(accData)
		self.accData={
			"mean_point":meanPoint,
			"raw":accData,
			"shifted":accData-meanPoint
		}
		return self.accData
	def fit_projectionLine( self ):

		accData= self.accData["raw"]
		# linregress method
		kmeanObj = get_KmeansSklearn( 2, accData )
		self.projectionLine["data"]=vector_to_complex(kmeanObj.cluster_centers_)	
		return self.projectionLine

	def cal_projectedData( self ):
		
		self.accData["projected"]=get_projectedIQDistance_byTwoPt(self.projectionLine["data"],self.accData["raw"])
		return self.accData["projected"]

	def cal_distribution( self ):

		distributionData = histogram(self.accData["projected"], bins='auto')
		devData = std(self.accData["projected"])
		xAxis = distributionData[1][1:] +(distributionData[1][1]-distributionData[1][0])/2
		distCount = distributionData[0]/float(len(distributionData[0]))
		midPoint = (xAxis[0]+xAxis[-1])/2

		guess = array([ 0.1, midPoint+devData*1.2, devData/2, 0.1, midPoint-devData*1.2, devData/2])
                                                                                                                               
		self.distribution={
			"x":xAxis,
			"count":distCount,
			"fitted":[],
		}
		try:
			popt,pcov=curve_fit(twoGaussian_func,xAxis, distCount, p0=guess)
			fitSuccess = True
			print("Good fitting", popt)
			self.distribution["fitted"]=gaussian_func(xAxis,popt[0:3])+gaussian_func(xAxis,popt[3:6])
		except:
			fitSuccess = False
			print("Bad fitting")
			self.distribution["fitted"]=gaussian_func(xAxis,guess[0:3])+gaussian_func(xAxis,guess[3:6])


		return self.distribution
	
	def do_analysis( self ):
		xAxisKey = self.quantificationObj.xAxisKey
		self.x = self.quantificationObj.independentVars[xAxisKey]
		# load the model from disk
		sav_file = "finalized_kmeans_model.sav"
		self.loaded_model = pickle.load(open(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\'+sav_file, 'rb'))
		self.i = self.quantificationObj.rawData["iqSignal"].real
		self.q = self.quantificationObj.rawData["iqSignal"].imag
		if len(self.i)==1:
			self.i1 = self.i[0]
			self.q1 = self.q[0]
			self.data = stack((self.i1, self.q1), axis=1)
			self.label = self.loaded_model.predict(self.data)
			text_report(self.label)
			self.fig, self.ax = plt.subplots(figsize=(12, 9))
			self.ax.axis('equal')
			plt.xlim(self.i1.min()-self.bleed, self.i1.max()+self.bleed)
			plt.ylim(self.q1.min()-self.bleed, self.q1.max()+self.bleed)
			#Getting unique labels
			self.u_labels = unique(self.label)
			#plotting the results:
			for i in self.u_labels:
				plt.scatter(self.i1[self.label == i] , self.q1[self.label == i] , label = self.label_list[i])
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=1,label=r'$1\sigma$', facecolor='pink', edgecolor='firebrick',alpha= 0.3)
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=2,label=r'$2\sigma$', edgecolor='fuchsia', linestyle='--')
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=3,label=r'$3\sigma$', edgecolor='blue', linestyle=':')
			self.diff = self.loaded_model.cluster_centers_[1]-self.loaded_model.cluster_centers_[0]
			self.k = self.diff[1]/self.diff[0]
			self.b = self.loaded_model.cluster_centers_[0][1]-self.k*self.loaded_model.cluster_centers_[0][0]
			self.b1 = self.loaded_model.cluster_centers_[0][1]+1/self.k*self.loaded_model.cluster_centers_[0][0]
			self.b2 = self.loaded_model.cluster_centers_[1][1]+1/self.k*self.loaded_model.cluster_centers_[1][0]
			self.line = np.linspace(self.i1.min(), self.i1.max(), 1000)
			self.ax.plot(self.line, self.k*self.line+self.b,color = "k")
			self.ax.plot(self.line, -1/self.k*self.line+self.b1,color = "r")
			self.ax.plot(self.line, -1/self.k*self.line+self.b2,color = "r")
			text_report(self.label)

			#plotting the results:
			for i in self.u_labels:
				self.ax.scatter(self.data.T[0][self.label == i] , self.data.T[1][self.label == i] , label = self.label_list[i])


			# plot_svm_decision_function(kmeans)
			for i in range(len(self.loaded_model.cluster_centers_)):
				self.ax.scatter(self.loaded_model.cluster_centers_[i][0],self.loaded_model.cluster_centers_[i][1],color = "r")

			for i in self.u_labels:
				self.cov = np.cov(self.data.T[0][self.label == i], self.data.T[1][self.label == i])
				print("{:<10}".format("The I-std div of ")+"{:<8}".format(self.label_list[i])+"state"+" : {:.4f}".format(np.sqrt(self.cov[0][0])))
				print("{:<10}".format("The Q-std div of ")+"{:<8}".format(self.label_list[i])+"state"+" : {:.4f}".format(np.sqrt(self.cov[1][1])))

			self.ax.legend()
			plt.title("readout_fidelity"+)
			plt.axis('equal')
			plt.savefig(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\fitness.png')
			# plt.show()
		else:
			yAxisKey = self.quantificationObj.yAxisKey
			self.y = self.quantificationObj.independentVars[yAxisKey]
			self.probability = []
			for self.times in range(len(self.i)):
				self.i2 = self.i[self.times]
				self.q2 = self.q[self.times]
				self.data = stack((self.i2, self.q2), axis=1)
				self.label = self.loaded_model.predict(self.data)
				self.u_unique, self.counts = unique(self.label, return_counts=True)
				self.probtmp = 100*self.counts[0]/(self.counts[0]+self.counts[1])
				self.probability.append(self.probtmp)
				print("{:d} times : ".format(self.times+1)+"{:<31}".format("The percentage of excited state")+" : {:.2f}%".format(self.probtmp))
			plt.figure()
			plt.rcParams["figure.figsize"] = (12, 9)
			plt.plot(self.y, self.probability)
			plt.savefig(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\fitness.png')

	def pre_analytic( self ):
		xAxisKey = self.quantificationObj.xAxisKey
		self.x = self.quantificationObj.independentVars[xAxisKey]
		self.i = self.quantificationObj.rawData["iqSignal"].real[0]
		self.q = self.quantificationObj.rawData["iqSignal"].imag[0]
		self.data = stack((self.i, self.q), axis=1)
		print(self.data)
		print(len(self.data))
		print('--------')
		self.kmeans = KMeans(n_clusters=2)
		self.kmeans.fit(self.data)
		# save the model to disk
		pickle.dump(self.kmeans, open(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\finalized_kmeans_model.sav', 'wb'))
		print("finished pretrain!")

# if __name__ == "__main__":
# 	worker_fresp(int(sys.argv[1]),int(sys.argv[2]))

def gaussian_func ( x, p):
	# p: amp, mean, sigma
	return p[0]/(p[2]*sqrt(2*pi))*exp( -1./2.*((x-p[1])/p[2])**2 )

def twoGaussian_func (x, *p):
	# p: ex_amp, ex_mean, ex_sigma, g_amp, g_mean, g_sigma
	exPars = (p[0],p[1],p[2])
	if p[1]-p[4]<amin([p[2],p[5]])/10:
		p[4]=p[1]-amin([p[2],p[5]])/10
	gndPars = (p[3],p[4],p[5])
	return gaussian_func(x,exPars)+gaussian_func(x,gndPars)


def expDecay_func ( x, p ):
	# p: amp, tau, offset
	return p[0]*exp(-x/p[1])+p[2]
def fit_ExpDecay_func ( x, *p ):
	if len(p)==5:
		# p: tau, IAmp, Ioffset, QAmp, Qoffset
		parsI = (p[1], p[0], p[2])
		parsQ = (p[3], p[0], p[4])
		return concatenate( (expDecay_func( x, parsI), expDecay_func( x, parsQ )) )
	elif len(p)==3:
		return expDecay_func( x, p )
def get_ExpDecay_fitCurve ( x, p, signalType ):
	if signalType=="indpendent":
		# p: tau, IAmp, Ioffset, QAmp, Qoffset
		parsI = (p[1], p[0], p[2])
		parsQ = (p[3], p[0], p[4])
		return expDecay_func( x, parsI )+1j*expDecay_func( x, parsQ )
	elif signalType=="phase":
		return exp(1j*expDecay_func( x, p ))
	elif signalType=="amp":
		return expDecay_func( x, p )

def RabiOscillation ( x, p):
	# p: amp, tau, freq, phi, offset
	return p[0]*exp(-x/p[1])*cos(2*pi*p[2]*x+p[3])+p[4]
def fit_RabiOscillation_func ( x, *p):
	if len(p)==7:
		# p: 0:tau, 1:freq, 2:phi, 3:IAmp, 4:Ioffset, 5:QAmp, 6:Qoffset
		parsI = (p[3], p[0], p[1], p[2], p[4])
		parsQ = (p[5], p[0], p[1], p[2], p[6])
		return concatenate( (RabiOscillation( x, parsI), RabiOscillation( x, parsQ)) )
	elif len(p)==5:	
		# p: 0:amp, 1:tau, 2:freq, 3:phi, 4:offset
		return RabiOscillation(x,p)
def get_RabiOscillation_fitCurve ( x, p, signalType ):
	if signalType=="indpendent":
		# p: 0:tau, 1:freq, 2:phi, 3:IAmp, 4:Ioffset, 5:QAmp, 6:Qoffset
		parsI = (p[3], p[0], p[1], p[2], p[4])
		parsQ = (p[5], p[0], p[1], p[2], p[6])
		return RabiOscillation( x, parsI )+1j*RabiOscillation( x, parsQ )
	elif signalType=="phase":
		return exp(1j*RabiOscillation( x, p ))
	elif signalType=="amp":
		return RabiOscillation( x, p )

class Common_fitting():

	def __init__( self, quantificationObj, *args,**kwargs ):

		self.quantificationObj = quantificationObj

		# Fit
		self.fitCurve = {}
		self.fitResult = {}

		self._fitParameters = None
		#self._init_fitResult()
		
		self._init_fitCurve()



	def _init_fitResult( self, yAxisLen=0, paraNames=[] ):
		nanArray = empty([yAxisLen])
		nanArray.fill( nan )
		fitParas = self.fitParameters

		# set names of fitting parameters
		if paraNames==[]:
			if fitParas["function"]=="ExpDecay":
				if fitParas["signal_type"]=="indpendent":
					paraNames= ["tau","ampI","offsetI","ampQ","offsetQ"]
				else:
					paraNames= ["amp","tau","offset"]

			elif fitParas["function"]=="RabiOscillation":
				if fitParas["signal_type"]=="indpendent":
					paraNames= ["tau", "frequency", "phi", "ampI", "offsetI", "ampQ", "offsetQ"]
				else:
					paraNames= ["amp","tau", "frequency", "phi", "offset"]
		self.paraNames =paraNames
		self.fitResult ={}
		for rk in paraNames:
			self.fitResult[rk]={}
			self.fitResult[rk]["value"] = nanArray.copy()
			self.fitResult[rk]["error"] = nanArray.copy()



	def _init_fitCurve( self, yAxisLen=0, xAxisLen=0 ):
		self.fitCurve = {
			"x": empty([xAxisLen]),
			"iqSignal": empty([yAxisLen,xAxisLen], dtype=complex),
		}

	@property
	def fitParameters(self):
		return self._fitParameters

	@fitParameters.setter
	def fitParameters(self, fitParameters=None):
		if fitParameters == None:
			fitParameters={
				"function": "ExpDecay",
				"signal_type": "indpendent",
				"range": 0,
			}
		else:
			try:
			# convert string to float list
				fitRange = [float(k) for k in fitParameters["range"].split(",")]
				fitParameters["range"] = fitRange
			except:
				xData= self.quantificationObj.rawData["x"]
				fitParameters["range"] =[amin(xData),amax(xData)]
				
		self._fitParameters = fitParameters


	def amp_signal (self, yInd, mask):
		data = abs(self.quantificationObj.rawData["iqSignal"][yInd])[mask]
		return data
	def phase_signal (self, yInd, mask):
		data = angle(self.quantificationObj.rawData["iqSignal"][yInd])[mask]
		return data
	def indpendent_signal (self, yInd, mask):
		dataRe = self.quantificationObj.rawData["iqSignal"][yInd].real[mask]
		dataIm = self.quantificationObj.rawData["iqSignal"][yInd].imag[mask]
		data = append(dataRe,dataIm)
		return data


	def do_analysis( self ):

		qObj = self.quantificationObj
		xAxisLen = qObj.rawData["x"].shape[0]
		fitParas = self.fitParameters
		signalType = {
			'amp': self.amp_signal,
			'phase': self.phase_signal,
			'indpendent': self.indpendent_signal,
		}


				
		def fit_ExpDecay ( yInd, mask ) :
			guess = array([])
			data=signalType[fitParas["signal_type"]](yInd, mask)
			# Guess initial value
			if fitParas["signal_type"] == "indpendent":
				dataRe = qObj.rawData["iqSignal"][yInd].real
				dataIm = qObj.rawData["iqSignal"][yInd].imag
				guess = array([4000,dataRe[0]-dataRe[-1],dataRe[-1],dataIm[0],dataIm[-1]])
			else:
				# p: tau, IAmp, Ioffset, QAmp, Qoffset
				guess = array([data[0]-data[-1],4000,data[-1]])

			popt,pcov= curve_fit(fit_ExpDecay_func,qObj.rawData["x"][mask],data,p0=guess)
			return popt,pcov
		def fit_Rabi ( yInd, mask ) :
			guess = array([])

			data=signalType[fitParas["signal_type"]](yInd, mask)
			# Guess initial value
			timeStep= qObj.rawData["x"][mask][1]-qObj.rawData["x"][mask][0]
			freqAxis= fftfreq(qObj.rawData["iqSignal"][yInd].shape[-1],timeStep)
			freqInd=1
			# p: 0:tau, 1:omega, 2:phi, 3:IAmp, 4:Ioffset, 5:QAmp, 6:Qoffset
			if fitParas["signal_type"] == "indpendent":
				dataRe = qObj.rawData["iqSignal"][yInd].real
				dataIm = qObj.rawData["iqSignal"][yInd].imag
				if amax(fft(dataRe-mean(dataRe))) > amax(fft(dataIm-mean(dataIm))):
					freqInd = argmax( fft(dataRe) )
				else:
					freqInd = argmax( fft(dataIm) )

				guess = array([2000,abs(freqAxis[freqInd]),0,dataRe[0]-mean(dataRe),mean(dataRe),dataIm[0]-mean(dataIm),mean(dataIm)])
			else:
				# p: 0:amp, 1:tau, 2:omega, 3:phi, 4:offset
				freqInd = argmax(fft(data-mean(data)))
				guess = array([data[0]-mean(data),2000,abs(freqAxis[freqInd]),0,mean(data)])
			popt,pcov= curve_fit(fit_RabiOscillation_func,qObj.rawData["x"][mask],data,p0=guess)

			return popt,pcov
		fit = {
			'ExpDecay': fit_ExpDecay,
			'RabiOscillation': fit_Rabi,
		}
		getFitCurve = {
			'ExpDecay': get_ExpDecay_fitCurve,
			'RabiOscillation': get_RabiOscillation_fitCurve,
		}		



		# Get 1D or 2D data to self.rawData
		if qObj.yAxisKey == None:
			yAxisLen = 1
		else:
			yAxisLen = qObj.independentVars[qObj.yAxisKey].shape[0]
		
		self._init_fitCurve(yAxisLen=yAxisLen,xAxisLen=xAxisLen)
		self._init_fitResult(yAxisLen=yAxisLen)

		# Set x-axis (frequency) of fit curve 
		fitRangeBoolean = logical_and(qObj.rawData["x"]>=fitParas["range"][0],qObj.rawData["x"]<=fitParas["range"][1]) 
		self.fitCurve["x"] = qObj.rawData["x"]

		for i in range(yAxisLen):
			
			try:
			# 	# Fit
				popt,pcov= fit[fitParas["function"]](i, fitRangeBoolean)
				fitSuccess = True
			#print("Good fitting")

			except:
				fitSuccess = False
				print("Bad fitting")
			if fitSuccess:
				self.fitCurve["iqSignal"][i] = getFitCurve[fitParas["function"]]( qObj.rawData["x"], popt, fitParas["signal_type"])
				perr = sqrt(diag(pcov))

				for ki, k in enumerate(self.paraNames):
					if perr[ki] < abs(popt[ki])*10 :
						self.fitResult[k]["value"][i] = popt[ki]
						self.fitResult[k]["error"][i] = perr[ki]

def fit_plot(i,ax,coef):return coef[0]*ax*ax+coef[1]*ax+coef[2]

def fit_sin(tt, yy):
	'''Fit sin to the input time sequence, and return fitting parameters "amp", "omega", "phase", "offset", "freq", "period" and "fitfunc"'''
	tt = array(tt)
	yy = array(yy)
	ff = fftfreq(len(tt), (tt[1]-tt[0]))   # assume uniform spacing
	Fyy = abs(fft(yy))
	guess_freq = abs(ff[argmax(Fyy[1:])+1])   # excluding the zero frequency "peak", which is related to offset
	guess_amp = std(yy) * 2.**0.5
	guess_offset = mean(yy)
	guess = array([guess_amp, 2.*pi*guess_freq, 0., guess_offset])

	def sinfunc(t, A, w, p, c):  return A * sin(w*t + p) + c
	popt, pcov = curve_fit(sinfunc, tt, yy, p0=guess)
	A, w, p, c = popt
	f = w/(2.*pi)
	fitfunc = lambda t: A * sin(w*t + p) + c
	output = {"amp": A, "omega": w, "phase": p, "offset": c, "freq": f, "period": 1./f, "fitfunc": fitfunc, "maxcov": max(pcov), "rawres": (guess,popt,pcov)}
	return output

class Autoflux():

	def __init__( self, quantificationObj, *args,**kwargs ):

		self.quantificationObj = quantificationObj

		# Fit
		self.real, self.imag = [],[]
		self.flux,self.freq,self.I,self.Q= [],[],[],[]

	def do_analysis( self ):
		xAxisKey = self.quantificationObj.xAxisKey
		yAxisKey = self.quantificationObj.yAxisKey
		self.x = self.quantificationObj.independentVars[xAxisKey]
		self.y = self.quantificationObj.independentVars[yAxisKey]
		self.i = self.quantificationObj.rawData["iqSignal"].real
		self.q = self.quantificationObj.rawData["iqSignal"].imag
		self.iq = transpose(self.quantificationObj.rawData["iqSignal"])
		#---------------changeable variable---------------
		# x(ki) = g*g/delta
		self.ki = 0.003
		self.fdress = 8.1248
		self.plot = 1
		self.mat = 1

		#---------------prepare data ---------------
		self.df1=pd.DataFrame()
		for j in range(len(self.x)):
			self.port1 = notch_port(f_data=self.y,z_data_raw=self.iq[j])
			# port1.plotrawdata()
			self.port1.autofit()
			#     port1.plotall()
			#     display(pd.DataFrame([port1.fitresults]).applymap(lambda x: "{0:.2e}".format(x)))
			# print(self.port1.fitresults)
			self.df1 = self.df1.append(pd.DataFrame([self.port1.fitresults]), ignore_index = True)
		self.df1.insert(loc=0, column='flux', value=self.x*10**6)

		#---------------drop the outward data---------------
		self.f_min,self.f_max = min(self.y),max(self.y)
		self.valid = self.df1[(self.df1['fr']>= self.f_min)&(self.df1['fr']<= self.f_max)]
		self.valid.reset_index(inplace=True)
		# print(valid)
		#---------------determine the sin_wave or arcsin_wave
		if self.valid.diff(periods=1, axis=0)['fr'].var() >2.5*10**-5 and max(self.valid['fr'])-min(self.valid['fr'])>0.002 :self.twokind=1
		elif self.valid.diff(periods=1, axis=0)['fr'].var() <2.5*10**-5 and max(self.valid['fr'])-min(self.valid['fr'])<0.002:self.twokind=0
		else:raise ValueError('I do not know how')
		if self.twokind:
		#     print('fr>fc and fr<fc')
			self.fc ,self.fd, self.offset = output_cal(self.x,self.valid,self.ki,self.fdress,self.plot)
		else:
		#     print('sin')
			self.fc ,self.fd, self.offset = output_cal_sin(self.valid,self.plot)
			# print(type(offset))

		print("")
		print("{:<23}".format("Final_dressed frquency"), " : " , "{:.4f}".format(self.fd) ,"GHz")
		print("{:<23}".format("Final_cavity frquency"), " : " , "{:.4f}".format(self.fc) ,"GHz")
		print("{:<23}".format("Final_x(ki)"), " : " , "{:.4f}".format((self.fd-self.fc)*1000) ,"MHz")
		print("{:<23}".format("Final_offset flux")," : ",self.offset,"uV/A")

def plot_svm_decision_function(model, ax=None, plot_support=True):
	"""Plot the decision function for a 2D SVC"""
	if ax is None:
		ax = plt.gca()
	xlim = ax.get_xlim()
	ylim = ax.get_ylim()
	
	# create grid to evaluate model
	x = linspace(xlim[0], xlim[1], 30)
	y = linspace(ylim[0], ylim[1], 30)
	Y,X = meshgrid(y, x)
	xy = stack([X.ravel(), Y.ravel()]).T
	P = model.decision_function(xy).reshape(X.shape)
	
	# plot decision boundary and margins
	ax.contour(X, Y, P, colors='k',
			levels=[-1, 0, 1], alpha=0.5,
			linestyles=['--', '-', '--'])
	
	# plot support vectors
	if plot_support:
		ax.scatter(model.support_vectors_[:, 0],
				model.support_vectors_[:, 1],
				s=300, linewidth=1, facecolors='none')
	ax.set_xlim(xlim)
	ax.set_ylim(ylim)
	plt.axis('equal')
	

def text_report(label):
	label_list= ["gnd","exc"]
	u_unique, counts = unique(label, return_counts=True)
	print(dict(zip(label_list, counts)))
	print("{:<31}".format("The percentage of ground state")+" : {:.2f}%".format(100*counts[1]/(counts[0]+counts[1])))
	print("{:<31}".format("The percentage of excited state")+" : {:.2f}%".format(100*counts[0]/(counts[0]+counts[1])))

def confidence_ellipse(x, y, ax, n_std=3.0, facecolor='none', **kwargs):
	"""
	Create a plot of the covariance confidence ellipse of *x* and *y*.

	Parameters
	----------
	x, y : array-like, shape (n, )
		Input data.

	ax : matplotlib.axes.Axes
		The axes object to draw the ellipse into.

	n_std : float
		The number of standard deviations to determine the ellipse's radiuses.

	**kwargs
		Forwarded to `~matplotlib.patches.Ellipse`

	Returns
	-------
	matplotlib.patches.Ellipse
	"""
	if x.size != y.size:
		raise ValueError("x and y must be the same size")

	cov = np.cov(x, y)
	pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
	# Using a special case to obtain the eigenvalues of this
	# two-dimensionl dataset.
	ell_radius_x = np.sqrt(1 + pearson)
	ell_radius_y = np.sqrt(1 - pearson)
	ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
					facecolor=facecolor, **kwargs)

	# Calculating the stdandard deviation of x from
	# the squareroot of the variance and multiplying
	# with the given number of standard deviations.
	scale_x = np.sqrt(cov[0, 0]) * n_std
	mean_x = np.mean(x)

	# calculating the stdandard deviation of y ...
	scale_y = np.sqrt(cov[1, 1]) * n_std
	mean_y = np.mean(y)

	transf = transforms.Affine2D() \
		.rotate_deg(45) \
		.scale(scale_x, scale_y) \
		.translate(mean_x, mean_y)

	ellipse.set_transform(transf + ax.transData)
	return ax.add_patch(ellipse)

class Readout_fidelity():

	def __init__( self, quantificationObj, *args,**kwargs ):

		self.quantificationObj = quantificationObj

		# Fit
		self.real, self.imag = [],[]
		self.label_list= ["gnd","exc"]
		self.probability = []
		self.bleed = 10**-3

	
	
	def do_analysis( self ):
		xAxisKey = self.quantificationObj.xAxisKey
		self.x = self.quantificationObj.independentVars[xAxisKey]
		# load the model from disk
		self.loaded_model = pickle.load(open(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\finalized_kmeans_model.sav', 'rb'))
		self.i = self.quantificationObj.rawData["iqSignal"].real
		self.q = self.quantificationObj.rawData["iqSignal"].imag
		if len(self.i)==1:
			self.i1 = self.i[0]
			self.q1 = self.q[0]
			self.data = stack((self.i1, self.q1), axis=1)
			self.label = self.loaded_model.predict(self.data)
			text_report(self.label)
			self.fig, self.ax = plt.subplots(figsize=(12, 9))
			self.ax.axis('equal')
			plt.xlim(self.i1.min()-self.bleed, self.i1.max()+self.bleed)
			plt.ylim(self.q1.min()-self.bleed, self.q1.max()+self.bleed)
			#Getting unique labels
			self.u_labels = unique(self.label)
			#plotting the results:
			for i in self.u_labels:
				plt.scatter(self.i1[self.label == i] , self.q1[self.label == i] , label = self.label_list[i])
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=1,label=r'$1\sigma$', facecolor='pink', edgecolor='firebrick',alpha= 0.3)
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=2,label=r'$2\sigma$', edgecolor='fuchsia', linestyle='--')
				confidence_ellipse(self.data.T[0][self.label == i], self.data.T[1][self.label == i], self.ax, n_std=3,label=r'$3\sigma$', edgecolor='blue', linestyle=':')
			self.diff = self.loaded_model.cluster_centers_[1]-self.loaded_model.cluster_centers_[0]
			self.k = self.diff[1]/self.diff[0]
			self.b = self.loaded_model.cluster_centers_[0][1]-self.k*self.loaded_model.cluster_centers_[0][0]
			self.b1 = self.loaded_model.cluster_centers_[0][1]+1/self.k*self.loaded_model.cluster_centers_[0][0]
			self.b2 = self.loaded_model.cluster_centers_[1][1]+1/self.k*self.loaded_model.cluster_centers_[1][0]
			self.line = np.linspace(self.i1.min(), self.i1.max(), 1000)
			self.ax.plot(self.line, self.k*self.line+self.b,color = "k")
			self.ax.plot(self.line, -1/self.k*self.line+self.b1,color = "r")
			self.ax.plot(self.line, -1/self.k*self.line+self.b2,color = "r")
			text_report(self.label)

			#plotting the results:
			for i in self.u_labels:
				self.ax.scatter(self.data.T[0][self.label == i] , self.data.T[1][self.label == i] , label = self.label_list[i])


			# plot_svm_decision_function(kmeans)
			for i in range(len(self.loaded_model.cluster_centers_)):
				self.ax.scatter(self.loaded_model.cluster_centers_[i][0],self.loaded_model.cluster_centers_[i][1],color = "r")

			for i in self.u_labels:
				self.cov = np.cov(self.data.T[0][self.label == i], self.data.T[1][self.label == i])
				print("{:<10}".format("The I-std div of ")+"{:<8}".format(self.label_list[i])+"state"+" : {:.4f}".format(np.sqrt(self.cov[0][0])))
				print("{:<10}".format("The Q-std div of ")+"{:<8}".format(self.label_list[i])+"state"+" : {:.4f}".format(np.sqrt(self.cov[1][1])))

			self.ax.legend()
			plt.title("readout_fidelity")
			plt.axis('equal')
			plt.savefig(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\fitness.png')
			# plt.show()
		else:
			yAxisKey = self.quantificationObj.yAxisKey
			self.y = self.quantificationObj.independentVars[yAxisKey]
			self.probability = []
			for self.times in range(len(self.i)):
				self.i2 = self.i[self.times]
				self.q2 = self.q[self.times]
				self.data = stack((self.i2, self.q2), axis=1)
				self.label = self.loaded_model.predict(self.data)
				self.u_unique, self.counts = unique(self.label, return_counts=True)
				self.probtmp = 100*self.counts[0]/(self.counts[0]+self.counts[1])
				self.probability.append(self.probtmp)
				print("{:d} times : ".format(self.times+1)+"{:<31}".format("The percentage of excited state")+" : {:.2f}%".format(self.probtmp))
			plt.figure()
			plt.rcParams["figure.figsize"] = (12, 9)
			plt.plot(self.y, self.probability)
			plt.savefig(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\fitness.png')

	def pre_analytic( self ):
		xAxisKey = self.quantificationObj.xAxisKey
		self.x = self.quantificationObj.independentVars[xAxisKey]
		self.i = self.quantificationObj.rawData["iqSignal"].real[0]
		self.q = self.quantificationObj.rawData["iqSignal"].imag[0]
		self.data = stack((self.i, self.q), axis=1)
		print(self.data)
		print(len(self.data))
		print('--------')
		self.kmeans = KMeans(n_clusters=2)
		self.kmeans.fit(self.data)
		# save the model to disk
		pickle.dump(self.kmeans, open(r'C:\Users\ASQUM\Documents\GitHub\PYQUM\TEST\FACE\pyqum\static\img\finalized_kmeans_model.sav', 'wb'))
		print("finished pretrain!")

