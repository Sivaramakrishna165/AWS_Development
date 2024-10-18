import time

class Student:
    def setStudent(self):
        self.no=input("Enter sno : ")
        self.name=input("Enter name : ")

        self.d=self.Dob()
        self.d.setDob( )
        
        self.m=self.Marks()
        self.m.setMarks()
        

    def getStudent(self):
        print("Sno is : ",self.no)
        print("Sname is : ",self.name)
        print("================")
        self.d.getDob( )
        print("=================")
        self.m.getMarks()

    class Dob:
        def setDob(self):
            self.dd=input("Enter DD : ")
            self.mm=input("Enter MM : ")
            self.yy=input("Enter YY : ")

        def getDob(self):
            print(f"Dob is : {self.dd}-{self.mm}-{self.yy}")

    class Marks:
        def setMarks(self):
            print("Enter Marks ")
            self.marks=[int(i) for i in input().split()]

        def getMarks(self):
            print("Marks are : ",self.marks)
            for i in self.marks:
                time.sleep(.2)
                print(i)
            print("Total is : ",sum(self.marks))
            
''' calling '''
s=Student()
s.setStudent()
s.getStudent()



        
