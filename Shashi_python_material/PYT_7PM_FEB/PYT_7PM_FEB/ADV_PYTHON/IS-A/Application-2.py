
class Person:
    def  setPerson(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")

    def getPerson(self):
        print("sno is : ",self.no)
        print("sname is : ",self.name)

class Marks(Person):
    def setMarks(self):
        self.m1=int(input("Enter m1 : "))
        self.m2=int(input("Enter m2 : "))
        self.m3=int(input("Enter m3 : "))

    def getMarks(self):
        self.tot=self.m1+self.m2+self.m3
        self.avg=self.tot/3
        print("==================")
        print("M1 : ",self.m1)
        print("M2 : ",self.m2)
        print("M3 : ",self.m3)
        print("==================")
        print("Total is : ",self.tot)
        print("Avg is : ",self.avg)
        print("===================")

class Student(Marks):
    def setStudent(self):
        self.setPerson()
        self.setMarks()

    def getStudent(self):
        self.getPerson()
        self.getMarks()

''' calling '''
s=Student()
s.setStudent()
s.getStudent()











        
