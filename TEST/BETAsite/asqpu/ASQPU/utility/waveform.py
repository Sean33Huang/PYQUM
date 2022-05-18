
# Numpy Series
# Typing
from numpy import ndarray

from numpy import array, linspace

class waveform():
    """ Data format for the f(x) with linear x input"""
    def __init__( self, x0:float=0, dx:float=1, Y:ndarray=array([]) ):
        self.x0 = x0
        self.dx = dx
        self.Y = Y

    @property
    def Y ( self )->ndarray:
        return self._Y
    @Y.setter
    def Y ( self, value:ndarray ):
        self._Y = value
        self._points = value.shape[-1]

    @property
    def x0 ( self )->ndarray:
        return self._x0
    @x0.setter
    def x0 ( self, value:float ):
        self._x0 = value

    @property
    def dx ( self )->ndarray:
        return self._dx
    @dx.setter
    def dx ( self, value:ndarray ):
        self._dx = value

    @property
    def points ( self )->int:
        """ Array length of Y """
        return self._points

    def get_xAxis ( self ):
        return linspace(self.x0, self.x0+self.dx*self.points,self.points, endpoint=False)

if __name__ == '__main__':
    a = waveform()
    a.dx = 2
    a.Y = array([10,20,30])
    print(a.get_xAxis())