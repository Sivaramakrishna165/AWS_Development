
#range(stop) -> range object | iterable
r=range(10)
print("Type is : ",type(r))
print("Range object : ",r) #range(0,10)

import time
for i in r:
    time.sleep(.2)
    print(i)

print("=============================")

#range(stop) -> range object | iterable
#range(start,stop[,step]) -> range object | iterable

r=range(2,21,2)
for i in r:
    time.sleep(.2)
    print(i)

















