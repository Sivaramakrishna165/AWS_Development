
from abc import ABC,abstractmethod

class Shapes(ABC):
    def setShapes(self,dim1,dim2):
        self.dim1=dim1
        self.dim2=dim2

    @abstractmethod
    def findArea(self):
        pass

class Triangle(Shapes):
    def findArea(self):
        return 0.5*self.dim1*self.dim2

class Rect(Shapes):
    def findArea(self):
        return self.dim1*self.dim2

#calling
t=Triangle()
t.setShapes(5,5)
at=t.findArea( )
print("Area of Triangle : ",at)
print("-"*30)

r=Rect()
r.setShapes(5,5)
ar=r.findArea( )
print("Area of Rect : ",ar)












    
