
class Sample:
    x=10 #static variable

    def method1(self):
        x=30 #local variable
        self.x=20 #inst
        print("mtd-1 of Sample")
        print("x val is : ",x)
        print("Ins x val is : ",self.x)
        print("static x val is : ",Sample.x)

''' calling '''
s=Sample()
s.method1()

