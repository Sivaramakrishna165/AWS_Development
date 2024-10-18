class Student:
    course="Python"
    
    def setStudent(self,no,name):
        self.no=no
        self.name=name

    def getStudent(self):
        print("sno is : ",self.no)
        print("sname is : ",self.name)
        print("course is : ",Student.course)

''' calling '''
s1=Student()
s1.setStudent(101,"Ramesh")
s1.getStudent()
print("=======================")


s2=Student()
s2.setStudent(201,"Suresh")
s2.getStudent()

Student.course="Django"
s1.getStudent()




        
        
