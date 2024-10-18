
class Test:
    def __init__(self):
        self._x=10 #protected

    def getData(self):
        print("Test  protected x : ",self._x)

class Testing(Test):
    def getData2(self):
        print("Testing protected x : ",self._x)

#calling
t=Testing()
t.getData( )
t.getData2( )
