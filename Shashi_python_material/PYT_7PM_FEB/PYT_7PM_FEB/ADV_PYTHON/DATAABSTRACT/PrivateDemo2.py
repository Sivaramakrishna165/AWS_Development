
class Super:
    def __init__(self):
        self.__x=10  #private

    def method1(self):
        print("mtd-1 of Super ")
        print("x val is : ",self.__x)

class Sub(Super):
    def method2(self):
        print("mtd-1 of Sub")
        print("x val is : ",self.__x)

#calling
s=Super()
s.method1()

sb=Sub()
#sb.method2() AttributeError
print("From outside of the class")
print("private x : ",s.__x)








