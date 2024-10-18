
class Test:
    def __init__(self):
        self.x=10 #public

    def getData(self):
        print("Test x : ",self.x)

#calling
t=Test()
t.getData( )
print("From outside of the class ")
print("x val is : ",t.x)
