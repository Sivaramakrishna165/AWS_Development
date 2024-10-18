
#mymodule.py

class Employee:
    def __init__(self):
        self.eno=input("Enter eno : ")
        self.ename=input("Enter ename: ")
        self.ecity=input("Enter ecity : ")

    def getEmployee(self):
        print("eno is : ",self.eno)
        print("ename is : ",self.ename)
        print("ecity is : ",self.ecity)
        print("=====================")

        
