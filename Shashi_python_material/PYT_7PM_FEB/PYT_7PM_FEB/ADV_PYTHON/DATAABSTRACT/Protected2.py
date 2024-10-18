
class Super:
    def __init__(self):
        self._x=10  #protected

    def method1(self):
        print("mtd-1 of Super")
        print("protected x : ",self._x)

class Sub(Super):
    def method2(self):
        print("Mtd-2 of Sub")
        print("protected x : ",self._x)

#calling
s=Super()
s.method1()
print("=============")

sb=Sub()
sb.method2()


