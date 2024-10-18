
class Triangle:
    def __init__(self,base,height):
        self.base=base
        self.height=height
        self.findArea()

    def findArea(self):
        print("Result is : ",0.5*self.base*self.height)
    

''' calling '''
b=eval(input("Enter Base of Triangle : "))
h=eval(input("Enter Height Of Triangle : "))
t=Triangle(b,h)
#at=t.findArea( )
#print("Area of Triangle : ",at)
