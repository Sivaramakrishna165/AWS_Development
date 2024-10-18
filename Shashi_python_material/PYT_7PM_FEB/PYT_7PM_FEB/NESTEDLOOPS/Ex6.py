
import time

n=int(input("Enter No.of.Rows : "))
for o in range(1,n+1):
    for i in range(1,o+1):
        time.sleep(.2)
        print("*",end=' ')
    print(" ")
