
class Super:
    def __init__(self):
        self.x=10 #public

    def method1(self):
        print("mtd-1 of Super")
        print("public x : ",self.x)

class Sub(Super):
    def method2(self):
        print("mtd-2 of Sub")
        print("public x : ",self.x)

#calling
s=Sub()
s.method1()
s.method2()
print("From outside of the class")
print("public x val is : ",s.x)



