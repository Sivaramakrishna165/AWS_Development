
#range(stop) -> range object | iterable
#range(10)  -> range(0,10)

import time

r=range(10)
print("type is  : ",type(r))
print("range object : ",r)

for i in r:
    time.sleep(.2)
    print(i)
