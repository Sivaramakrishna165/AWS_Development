
class Sample:
    def __init__(self):
        self.x=10
        self.y=20

    def getData(self):
        print("x val is : ",self.x)
        print("y val is : ",self.y)

''' calling '''
s1=Sample()
print("Data from s1")
s1.getData()
print("==========")
s1=None
s1.getData( ) #AttributeError

s2=Sample( )
print("Data From s2 ")
s2.getData( )



