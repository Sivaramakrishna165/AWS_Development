
class Student:
    course="Python"

    def setStudent(self,no,name):
        self.no=no
        self.name=name

    def getStudent(self):
        print("no is : ",self.no)
        print("name is : ",self.name)
        print("course is : ",Student.course)
        print("=========================")
        
#calling
s1=Student()
s1.setStudent(101,"Ramesh")
s1.getStudent()

s2=Student()
s2.setStudent(102,"Roja")
s2.getStudent()



