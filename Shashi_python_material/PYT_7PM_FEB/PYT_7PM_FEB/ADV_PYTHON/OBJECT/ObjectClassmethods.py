import mymodule

e=mymodule.Employee()

print("Module Name is  : ",e.__module__)
print("ClassName is : ",e.__class__)
print("Doc String is : \n ",e.__doc__)

print("==========================")
e.getEmployee()

#Adding an instance Field to Employee object
#e.job='Manager'
e.__setattr__('job','MANAGER')
e.__setattr__('sal',90000)

import time
for k,d in e.__dict__.items():
    time.sleep(.2)
    print(k,d,sep=" <<<>>> ")
print("============================")

#Reading value of an instance field
#name=e.ename
name=e.__getattribute__('ename')
print("Name is : ",name)

print("=========================")

#Deleting an instance field from the object
#del e.ename
e.__delattr__('ename')
e.__delattr__('job')
print( e.__dict__)





















