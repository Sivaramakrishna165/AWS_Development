import time
n=int(input("Enter a number : "))

f=i=1
while i<=n:
    time.sleep(.2)
    f*=i
    i=i+1
print("Fact is : ",f)

print("==================")
import math
r=math.factorial(n)
print("Result is : ",r)

