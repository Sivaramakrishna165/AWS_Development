import time

lst=[30,40,20,10,60,70,80]
print("List : ",lst)
found=False

sn=int(input("Enter Search No : ")) #20

for i in lst:
    time.sleep(.2)
    if i==sn:
        print("Found")
        found=True
        break

if not found:
    print("Sorry Not Found")
    
    
