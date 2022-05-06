
from cProfile import label
from numpy import array, reshape, mean, transpose, ndarray
from sklearn.cluster import KMeans



def get_KmeansSklearn( n_clusters, iqComplex )->KMeans:
    data = complex_to_vector(iqComplex, vectorShape="H")
    kmeans = KMeans(n_clusters=n_clusters,tol=1e-4).fit(data)
    return kmeans

def get_population( iqCenter:ndarray, iqComplex:ndarray ):
    #print(iqCenter, iqComplex)
    myKmean = get_KmeansSklearn(2,iqCenter)
    iqVectData = complex_to_vector(iqComplex,vectorShape="H")
    clusterData = myKmean.predict(iqVectData.reshape((iqComplex.size,2)))

    return mean(clusterData.reshape(iqComplex.shape),axis=iqComplex.ndim-1)

def complex_to_vector( complexArray:ndarray, vectorShape="V" ):
    """
    complexArray is array of complex number which dimension is N, 
    the real and image part will becom two element in new dimension k.
    The dimension of the return array is N+1.
    Maximum dimension of 'complexArray' is 2 (i,j)
    i is the first dimension axis, j is the second.

    vectorShape define the index of new dimension k
    "V" k put at N th dimention
    "H" k put at N-1 th dimention

    """
    transArr = array([complexArray.real,complexArray.imag])
    arrayDim = complexArray.ndim
    if vectorShape == "V":
        if arrayDim == 2:
            return transArr.transpose((1,0,2))
        if arrayDim == 1:
            return transArr.transpose((0,1))
        return transArr
    elif "H":
        if arrayDim == 2:
            return transArr.transpose((1,2,0))
        if arrayDim == 1:
            return transArr.transpose((1,0))

def vector_to_complex( vectorArray ):
    newVectorArray = vectorArray.transpose()
    print(newVectorArray)
    complexArray = newVectorArray[0]+1j*newVectorArray[1]
    return complexArray

def get_projectedIQVector_byTwoPt( projComplex, iqComplex ):
    refPoint = projComplex[0]
    shiftedIQComplex = iqComplex-refPoint
    relativeProjComplex = projComplex[1]-refPoint
    projectionVector = complex_to_vector(array([relativeProjComplex]),"H")
    shiftedIQVector = complex_to_vector(shiftedIQComplex,"V")
    projectionMatrix = projectionVector.transpose()@projectionVector/abs(relativeProjComplex)**2
    projectedVector = projectionMatrix@shiftedIQVector
    return projectedVector

def get_projectedIQDistance_byTwoPt( projComplex:ndarray, iqComplex:ndarray ):
    refPoint = projComplex[1]
    shiftedIQComplex = iqComplex-refPoint
    relativeProjComplex = projComplex[0]-refPoint
    projectionVector = complex_to_vector(array([relativeProjComplex]),"H")
    shiftedIQVector = complex_to_vector(shiftedIQComplex,"V")
    #print(projectionVector.shape,shiftedIQVector.shape)
    projectedDistance = projectionVector@shiftedIQVector/abs(relativeProjComplex)
    return projectedDistance[0]

def get_simulationData(measurementPts, excitedProbability, iqPosition, sigma)->ndarray:
    excPts = int(measurementPts*excitedProbability)
    groundProbability = 1-excitedProbability
    groundPts = int(measurementPts*groundProbability)
    gpos=iqPosition[0]
    epos=iqPosition[1]
    g = np.random.normal(gpos.real, sigma, groundPts)+1j*np.random.normal(gpos.imag, sigma, groundPts)
    e = np.random.normal(epos.real, sigma, excPts)+1j*np.random.normal(epos.imag, sigma, excPts)

    iqdata = np.append(g,e)    
    return iqdata

def get_oneShot_kmeanDistance(iqdata):

    km = get_KmeansSklearn(2,iqdata)
    clusterCenter = km.cluster_centers_.transpose()
    clusterCenter = clusterCenter[0]+1j*clusterCenter[1]
    projectedDistance = get_projectedIQDistance_byTwoPt(clusterCenter,iqdata)
    #b = get_projectedIQVector_byTwoPt(clusterCenter,iqdata)
    return projectedDistance

def get_oneshot_plot(iqdata,simIQCenter=None):
    km = get_KmeansSklearn(2,iqdata)
    clusterCenter = vector_to_complex(km.cluster_centers_)
    a = get_projectedIQDistance_byTwoPt(clusterCenter,iqdata)
    plt.figure(1)
    plt.plot( iqdata.real, iqdata.imag, "o", label="Data" )
    plt.plot( clusterCenter.real, clusterCenter.imag, "o", label="KMeans" )
    #if simIQCenter != None:
    simCenter = array(simIQCenter).transpose()
    plt.plot( simCenter.real, simCenter.imag,"ro", label="Simulation" )
    plt.figure(2)
    count, bins, ignored = plt.hist(a, 60, density=True)
    plt.show()
def population_test(simCenter,measurementPts,ProbabilityRange,statisticTest=20):
    statisticTest = int(statisticTest)
    errorDistanceMean = np.empty(ProbabilityRange.shape[-1])
    errorDistanceSTD = np.empty(ProbabilityRange.shape[-1])
    for i,excitedProbability in enumerate(ProbabilityRange):

        ed = np.empty(statisticTest)
        for j in range(statisticTest):
            km = get_KmeansSklearn(2,get_simulationData(measurementPts,excitedProbability,simCenter,sigma))
            clusterCenter = km.cluster_centers_.transpose()
            clusterCenter = clusterCenter[0]+1j*clusterCenter[1]
            errorDistanceP1 = mean(abs(simCenter.transpose()-clusterCenter))

            clusterCenterP2 = array([clusterCenter[1],clusterCenter[0]])
            errorDistanceP2 = mean(abs(simCenter.transpose()-clusterCenterP2))

            ed[j] = np.min([errorDistanceP1,errorDistanceP2])
        errorDistanceMean[i] = np.mean(ed)
        errorDistanceSTD[i] = np.std(ed)
    plt.figure(1)
    plt.errorbar( ProbabilityRange, errorDistanceMean, yerr=errorDistanceSTD, fmt="ro" )
    plt.show()
    
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import numpy as np


    simQICenter = array([1+1j,1+2j])
    #print(simQICenter)
    measurementPts = 1000
    sigma = 0.2
    #get_oneshot_plot(get_simulationData(measurementPts,0.5,simQICenter,sigma),simIQCenter=simQICenter)
    statisticTest = int(20)
    ProbabilityRange = np.linspace(0.1,0.9,9)
    # testComplex = array([[0+1j,1+1j],[2+2j,3+3j],[4+4j,5+5j]])
    # print(testComplex)
    # print(complex_to_vector(testComplex))
    # print(complex_to_vector(testComplex, vectorShape="H"))

    # testComplex = array([0+1j,2+3j])
    # print(testComplex)
    # print(complex_to_vector(testComplex))
    # print(complex_to_vector(testComplex, vectorShape="H"))
    # testComplex = array([[1,2],[3,4]])
    # print(vector_to_complex(testComplex))
    data = array([get_simulationData(measurementPts,0.5,simQICenter,sigma),get_simulationData(measurementPts,0.25,simQICenter,sigma),get_simulationData(measurementPts,0.5,simQICenter,sigma)])
    #data = get_simulationData(measurementPts,0.5,simQICenter,sigma)
    print(simQICenter.shape, data.shape)
    nData = get_projectedIQDistance_byTwoPt(simQICenter,data)
    print(nData.shape)
    #print(data)
    #print(get_population(simQICenter,data))
    #population_test(simCenter,measurementPts,ProbabilityRange,statisticTest=20)
    
    