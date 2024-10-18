
class Circle:
    def setCircle(self,rad):
        self.rad=rad

    def findArea(self):
        return 3.14*self.rad*self.rad
    
#calling
c=Circle( )
c.setCircle(2)
ac=c.findArea( )
print("Area of Circle : ",ac)
