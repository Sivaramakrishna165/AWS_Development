class Student:
    def setStudent(self):
        self.m1=int(input("Enter m1 : "))
        self.m2=int(input("Enter m2 : "))
        self.m3=int(input("Enter m3 : "))

    def findResult(self):
        self.tot=self.m1+self.m2+self.m3
        self.avg=self.tot/3
        print("Total is : ",self.tot)
        print("Avg is : ",self.avg)
        if self.m1>34 and self.m2>34 and self.m3>34:
            print("Pass")
        else:
            print("Fail")

''' calling '''
s=Student()
s.setStudent()
s.findResult()
print("=======================")

s2=Student()
s2.setStudent()
s2.findResult()


        
