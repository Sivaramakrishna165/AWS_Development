import time
n=int(input("Enter a number : "))

s=0
i=1
while i<=n:
    time.sleep(.2)
    s=s+i
    i=i+1
    print("Sum is : ",s)
