class Employee:
    def __init__(self):
        self.name=input("enter name : ")
        self.spd=int(input("enter spd : "))

    def __mul__(self,other):
        return self.spd*other.daysw

class TimeSheet:
    def __init__(self):
        self.daysw=int(input("no.of.days worked : "))

    def __mul__(self,other):
        return self.daysw*other.spd

#calling
e=Employee()
t=TimeSheet()
ns=t*e
print("NetSalary is : ",ns)





