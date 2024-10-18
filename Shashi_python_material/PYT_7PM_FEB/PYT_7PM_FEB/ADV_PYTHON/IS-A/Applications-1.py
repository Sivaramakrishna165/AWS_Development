class Person:
    def setPerson(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")

    def getPerson(self):
        print("sno is : ",self.no)
        print("sname is : ",self.name)

class Student(Person):
    def setStudent(self):
        self.setPerson()
        self.course=input("Enter Course : ")

    def getStudent(self):
        self.getPerson()
        print("course is : ",self.course)

''' calling '''
s=Student()
s.setStudent()
s.getStudent()

