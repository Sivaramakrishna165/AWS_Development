
class Super:
    def __init__(self):
        self.x=10 #public

    def method1(self):
        print("mtd-1 of Super")
        print("public x : ",self.x)

#calling
s=Super()
s.method1()
