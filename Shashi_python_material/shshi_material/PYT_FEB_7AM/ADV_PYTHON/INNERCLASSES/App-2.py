import time

class Student:
    def setStudent(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")
        print("--------------------------------")

        self.d=self.Dob()
        self.d.setDob( )
        
        self.m=self.Marks()
        self.m.setMarks()
        

    def getStudent(self):
        print("no is : ",self.no)
        print("name is : ",self.name)
        self.d.getDob()
        self.m.getMarks( )
        

    class Dob:
        def setDob(self):
            print("Enter Dob ")
            self.dd=input("Enter DD : ")
            self.mm=input("Enter MM : ")
            self.yy=input("Enter YY : ")

        def getDob(self):
            print("Dob is : {}-{}-{}"
                  .format(self.dd,self.mm,self.yy))
            #print(f"Dob is : {self.dd}-{self.mm}-{self.yy}")
            print("===================")

    class Marks:
        def setMarks(self):
            print("Enter marks ")
            self.marks=[int(i) for i in input().split()] #list            

        def getMarks(self):
            print("Marks are ")
            for i in self.marks:
                time.sleep(.2)
                print(i)
            print("===============")
            print("Total is : ",sum(self.marks))
            print("===============")

#calling
s=Student()
s.setStudent()
s.getStudent()





        
