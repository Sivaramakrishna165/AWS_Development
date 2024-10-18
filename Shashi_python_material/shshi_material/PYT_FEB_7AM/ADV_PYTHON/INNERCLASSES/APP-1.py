
class Employee:
    def setEmployee(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")

    def getEmployee(self):
        print("no is : ",self.no)
        print("name is : ",self.name)

    class Doj:
        def setDoj(self):
            print("Enter Doj : ")
            self.dd=input("Enter DD : ")
            self.mm=input("Enter MM : ")
            self.yy=input("Enter YY : ")

        def getDoj(self):
            print("Doj is : {}-{}-{}"
                  .format(self.dd,self.mm,self.yy) )

#calling
e=Employee()
e.setEmployee()

d=e.Doj()
d.setDoj()

e.getEmployee()
d.getDoj()








            

