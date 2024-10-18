
import time
n=int(input("Enter a number : "))

f=i=1
while i<=n:
    f=f*i
    i=i+1

print("Fact is : ",f)
print("=====================")

import math
r=math.factorial(n)  # factorial(int) -> int
print("Fact is : ",r)
