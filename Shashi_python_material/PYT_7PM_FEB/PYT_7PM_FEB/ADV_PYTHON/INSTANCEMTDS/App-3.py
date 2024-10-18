
class Sample:
    def setData(self,x,y):
        print("setData ")
        self.x=x
        self.y=y

    def getData(self):
        print("getData ")
        print("x val is : ",self.x)
        print("y val is : ",self.y)

#calling
s=Sample()
s.setData(10,20)
s.getData( )
