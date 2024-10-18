import time
class Employee:
    def __init__(self,**x):
        self.x=x

    def getEmployee(self):
        for k,d in self.x.items():
            time.sleep(.4)
            print(k,d,sep=" << >> ")
        print("===============")

#calling
e=Employee(eno=101,ename="James",ecity="hyd")
e.getEmployee()

e1=Employee(eno=102,ename="chinni")
e1.getEmployee()

e2=Employee(eno=103)
e2.getEmployee()

e3=Employee()
e3.getEmployee()











