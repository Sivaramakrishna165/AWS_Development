#second.py

import mymodule   #Userdefined
import time   #Predefined 

print( mymodule.lst )

for i in mymodule.lst:
    time.sleep(1)
    print(i)
print("==================")

print( mymodule.stu )

for k,d in mymodule.stu.items():
    time.sleep(1)
    print(k,d,sep=' <<>> ')

print("==================")

mymodule.greetings()









    






