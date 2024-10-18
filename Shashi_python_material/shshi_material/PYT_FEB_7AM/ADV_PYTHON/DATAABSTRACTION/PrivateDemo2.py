
class Sample:
    def setData(self):
        self.__x=10 #private
    
class Testing(Sample):
    def getData(self):
        print("Testing x : ",self.__x)

#calling
t=Testing()
t.setData( )
t.getData()
        
    
