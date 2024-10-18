import mymodule

e=mymodule.Employee()
print("ClassName ? : ",e.__class__)
print("Module Name ? : ",e.__module__)
print("DocString ? : \n ",e.__doc__)

#printing instance Field
#no=e.eno
no=e.__getattribute__('eno')
print("eno is : ",no)

#Adding instance field
e.ejob='Manager'
job=e.__getattribute__('ejob')
print("job is : ",job)

#To see all the fields and their value
einfo=e.__dict__
print(einfo)

import time
for k,d in e.__dict__.items():
    time.sleep(.5)
    print(k,d,sep=" <<<>>> ")

#Updating an existed Fields
#e.ejob='CEO'
e.__setattr__('ejob','CEO')
print(e.__dict__)
print("-------------------------------")

#Deleting an instance Field
#del e.ejob
e.__delattr__('ejob')
print(e.__dict__)








    

    





















