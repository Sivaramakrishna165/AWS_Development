
import time

n=int(input("Enter a number : "))

for j in range(1,n+1):    
    for i in range(1,11):
        time.sleep(.2)
        print(j," x ",i,"= " ,j*i)
    print(" ")

    #time.sleep(10)
    if j!=n:
        input("Press Enter to continue......")
