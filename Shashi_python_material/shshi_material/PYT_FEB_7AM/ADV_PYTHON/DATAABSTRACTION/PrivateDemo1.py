
class Sample:
    def __init__(self):
        self.__x=10 #private

    def getData(self):
        print("From Sample ")
        print("getData x : ",self.__x)

#calling
s=Sample()
s.getData( )
