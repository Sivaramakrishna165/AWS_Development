
class Student:
    def setStudent(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")
        self.tot=int(input("Enter tot : "))

    def getStudent(self):
        print("sno is : ",self.no)
        print("sname is : ",self.name)
        print("total is : ",self.tot)

    def __gt__(self,other):
        if self.tot>other.tot:
            return True
        else:
            return False

#calling
s1=Student()
s1.setStudent()

s2=Student()
s2.setStudent()

if s1>s2:
    s1.getStudent()
else:
    s2.getStudent()


    


