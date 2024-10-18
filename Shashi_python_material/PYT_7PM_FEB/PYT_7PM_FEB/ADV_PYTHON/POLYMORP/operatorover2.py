
class Employee:
    def __init__(self):
        self.name=input("Enter name : ")
        self.spd=int(input("Enter sal per day :"))

    def __mul__(self,other):
        return self.spd*other.dayw

class TimeSheet:
    def __init__(self):
        self.dayw=int(input("Enter Days worked : "))

    def __mul__(self,other):
        return self.dayw*other.spd

''' calling '''
e=Employee()
t=TimeSheet()
ns=t*e
print("Netsalary is : ",ns)
