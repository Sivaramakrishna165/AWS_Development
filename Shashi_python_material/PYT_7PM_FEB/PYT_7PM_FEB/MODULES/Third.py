
import mymodule
import time

print("List : ",mymodule.lst)

for i in mymodule.lst:
    time.sleep(.2)
    print(i)

print("=====================")
print("Dict : ",mymodule.stu)

for k,d in mymodule.stu.items():
    time.sleep(.2)
    print(k,d,sep=' >>> ')

print("======================")

mymodule.myFun()






    
    
