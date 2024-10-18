#len(iterable) -> int

#        0                    1        2   3   4         
lst=["Ramesh","hyd",50,60,70]
print("List : ",lst)

import time

index=0
while index<len(lst):
    time.sleep(.5)
    print( lst[index] )
    index+=1
print("-"*30)

for i in lst:
    time.sleep(1)
    print(i)


    
    
