
from abc import ABC,abstractmethod

class Shapes(ABC):
    def setShapes(self,dim1,dim2):
        self.dim1=dim1
        self.dim2=dim2

    @abstractmethod
    def findArea(self):
        pass

class Rect(Shapes):
    def findArea(self):
        return self.dim1*self.dim2

class Triangle(Shapes):
    def findArea(self):
        return 0.5*self.dim1*self.dim2

''' calling '''
r=Rect()
r.setShapes(4,4)
ar=r.findArea()
print("Area of Rect : ",ar)
print("======================")

t=Triangle()
t.setShapes(5,5)
at=t.findArea()
print("Area of Triangle : ",at)







      




