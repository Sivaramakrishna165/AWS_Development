import time

class Person:
    def setPerson(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")

    def getPerson(self):
        print("no is : ",self.no)
        print("name is : ",self.name)
        print("-----------------------")

class Marks(Person):
    def setMarks(self):
        print("Enter sub marks ")
        self.marks=[int(i) for i in input().split()]  #list

    def getMarks(self):
        print("Marks : ")
        for i in self.marks:
            time.sleep(.2)
            print(i)
        print("===========")
        print("Total is : ",sum(self.marks))
        print("Avgt is : ",sum(self.marks)/len(self.marks))
        print("============")

class Student(Marks):
    def setStudent(self):
        self.setPerson()
        self.setMarks()

    def getStudent(self):
        self.getPerson()
        self.getMarks()

#calling
s=Student()
s.setStudent()
s.getStudent()



        
        




        









        
