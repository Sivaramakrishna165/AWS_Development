#       0    1          2           3
lst=[10,12.12,10+20j,"Shashi"]
print("List : ",lst)

#indexing
print("First : ",lst[0])
print("Last : ",lst[-1])

#slicing [ start : end :  step ]
print("First 3 objects : ",lst[0:3:1])
print("Last 3 object in rev : ",lst[-1:-4:-1])

#Reading all element
import time
index=0
while index<len(lst):
    time.sleep(1)
    print( lst[index] )
    index+=1
print("=======================")

for i in lst:
    time.sleep(.2)
    print(i)





    










    
