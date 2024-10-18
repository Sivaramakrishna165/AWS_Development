import time
import sys

lst=[i for i in range(1,100001)]
print("Type is : ",type(lst))
ls=sys.getsizeof(lst)
print("size for iterator : ",ls)
for i in lst:
    print(i)
    
print("===========================")
t=(i for i in range(1,100001))
print("Type is : ",type(t))
ts=sys.getsizeof(t)
print("size for generator : ",ts)

for i in t:
    print(i)

    
