import time

f=open("data1.txt","r")
time.sleep(1)
print("Is File Closed ? : ",f.closed)
f.close()
time.sleep(1)
print("Is File Closed ? : ",f.closed)
print("========================")

with open("data1.txt","r") as f:
    time.sleep(1)
    print("Inside of with context ")
    time.sleep(1)
    print("is File Closed ? ",f.closed)

time.sleep(1)
print("Outside of with context")
time.sleep(1)
print("is File Closed ? ",f.closed)







