
import time

#App-1
f=open("data3.txt")
print("Is File Closed ? : ",f.closed)
time.sleep(2)
f.close()
print("Is File Closed ? : ",f.closed)
print("========================")

#App-2
with open("data3.txt") as f:
    time.sleep(1)
    print("Inside of with context ")
    print("Is File Closed ? : ",f.closed)

time.sleep(1)
print("Outside of with context")
print("Is File Closed ? : ",f.closed)


