#len(iterable) -> int
#   0     1           2              3        4
t=(10,12.12,"shashi",None,10)
print("tuple : ",t)

#indexing
print("Second : ",t[1])
print("Last : ",t[-1])

#Slicing [start: end : step]
print("Objects are : ",t[1:4:1])

#Reading values:
import time

index=0
while index<len(t):
    time.sleep(1)
    print( t[index] )
    index+=1
print("======================")

for i in t:
    time.sleep(1)
    print(i)





    





    
    
