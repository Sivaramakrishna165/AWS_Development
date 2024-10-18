
class Super:
    def __init__(self):
        self.__x=10  #private

    def method1(self):
        print("mtd-1 of Super ")
        print("x val is : ",self.__x)

#calling
s=Super()
s.method1()
