
class Test:
    def __init__(self):
        self._x=10 #protected

    def getData(self):
        print("Test x : ",self._x)

#calling
t=Test()
t.getData()
