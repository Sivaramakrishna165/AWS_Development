
class Triangle:
    def __init__(self,base,height):
        self.base=base
        self.height=height

    def findArea(self):
        return self.base*self.height*0.5

#calling
print("Enter Base and height of Triangle : ")
t=Triangle( int(input()) , int(input()) ) 
at=t.findArea()
print("Area of Triangle : ",at)
