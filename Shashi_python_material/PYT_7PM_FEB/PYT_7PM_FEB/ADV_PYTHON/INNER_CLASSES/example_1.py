class Employee:
    def setEmployee(self):
        self.no=input("Enter Eno : ")
        self.name=input("Enter name : ")

    def getEmployee(self):
        print("Eno is : ",self.no)
        print("Ename is : ",self.name)

    class Doj:
        def setDoj(self):
            self.dd=input("Enter DD : ")
            self.mm=input("Enter MM : ")
            self.yy=input("Enter YY : ")

        def getDoj(self):
            print("DOJ is : {}-{}-{}"
                  .format(self.dd,self.mm,self.yy))
            
''' calling '''
e=Employee()
e.setEmployee()

d=e.Doj()
d.setDoj()

print("==============")
e.getEmployee()
d.getDoj()








                  

