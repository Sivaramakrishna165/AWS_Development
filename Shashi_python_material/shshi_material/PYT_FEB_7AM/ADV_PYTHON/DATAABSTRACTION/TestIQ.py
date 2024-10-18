
class Test:
    def __init__(self):
        self.__x=10 #private
        self._y=20   #protected
        self.z=30     #public

    def getData(self):
        print("private x : ",self.__x)
        print("protected y : ",self._y)
        print("public z : ",self.z)
        print("===================")


class Testing(Test):
    def getInfo(self):
        #print("private x : ",self.__x) AE
        print("protected y : ",self._y)
        print("public z : ",self.z)
        print("==================")

#calling
#t=Test()
#t.getData( )

t=Testing()
t.getData( )
t.getInfo()

print("From Outside of the class")
#print("private x : ",t.__x)
print("private x : ",t._Test__x)
print("protected y  : ",t._y)
print("public z : ",t.z)




        




