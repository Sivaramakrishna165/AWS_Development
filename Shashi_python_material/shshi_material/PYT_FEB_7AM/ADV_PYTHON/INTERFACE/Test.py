
from abc import ABC,abstractmethod

class Shapes(ABC):
    def setShapes(self,dim1,dim2):
        self.dim1=dim1
        self.dim2=dime

    @abstractmethod
    def findArea(self):
        pass

s=Shapes()
