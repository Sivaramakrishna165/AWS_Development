
class Super:
    def __init__(self):
        self.__x=10
        self._y=20
        self.z=30

    def method1(self):
        print("Mtd-1 of Super")
        print("Private x : ",self.__x)
        print("protected y : ",self._y)
        print("public z : ",self.z)
        print("=====================")

class Sub(Super):
    def method2(self):
        print("Mtd-2 of Sub")
        #print("private x : ",self.__x)
        print("protected y : ",self._y)
        print("public z : ",self.z)
        print("=====================")

#calling
s=Sub()
s.method1()
s.method2()
print("From outside of all the classes")
print("private x : ",s._Super__x)
print("protected y : ",s._y)
print("public z : ",s.z)

        




