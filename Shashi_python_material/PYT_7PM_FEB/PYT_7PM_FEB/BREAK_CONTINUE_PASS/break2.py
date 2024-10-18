


''' break and continue
     these are used only in the looping stmt(s)

     break vs exit( )
'''
import time

lst=[10,20,30,40,50,2,60,70]
print("List : ",lst)

sno=int( input("enter search no : ") ) #50
found=0

for i in lst:    
    if i==sno:
        print("Found ")
        found=1
        break

if found==0:
    print("Not Found ")
    
        
    














