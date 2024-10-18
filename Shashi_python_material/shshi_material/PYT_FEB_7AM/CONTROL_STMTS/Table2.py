
import time

n=int( input("Enter a number : ") )

for i in range(1,11,1):
    time.sleep(.2)
    print(n," x ",i," = ",n*i)
