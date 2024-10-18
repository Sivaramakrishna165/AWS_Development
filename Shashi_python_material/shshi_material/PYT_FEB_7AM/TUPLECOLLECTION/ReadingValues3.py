#     0    1                 2         3    4    5
t=(10,"Ramesh","Hyd",50,60,70)
print("Tuple : ",t)

import time
index=0
while index<len(t):
    time.sleep(.1)
    print(t[index])
    index+=1

print("===================")

for i in t:
    time.sleep(.2)
    print(i)


    

