
class Student:
    def __init__(self):
        self.no=input("Enter no : ")
        self.name=input("Enter name : ")
        self.tot=int(input("Enter tot : "))

    def getData(self):
        print("sno is : ",self.no)
        print("name is : ",self.name)
        print("total is : ",self.tot)

    def __gt__(self,other):
        if self.tot>other.tot:
            return True
        else:
            return False
        

''' calling '''
s1=Student()
s2=Student()
if s1>s2:
    s1.getData()
else:
    s2.getData()




    
