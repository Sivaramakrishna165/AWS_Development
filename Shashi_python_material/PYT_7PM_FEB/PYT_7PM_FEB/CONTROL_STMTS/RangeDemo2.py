
#range(stop) -> range object | iterable
#range(10)  -> range(0,10)
#===========================
#range(start,end[,step]) -> range object | iterable

import time
r=range(1,11,1)
print("Range Object : ",r)

for i in r:
    time.sleep(.2)
    print(i)

print("===========================")

r2=range(10,21,2)
for i in r2:
    time.sleep(.2)
    print(i)

print("===========================")

for a in range(1,21,2):
    time.sleep(.2)
    print(a)

print("============================")

for i in range(10,0,-1):
    time.sleep(.2)
    print(i)

print("===========================")

for i in range(1,11,0):
    time.sleep(.1)
    print(i)











