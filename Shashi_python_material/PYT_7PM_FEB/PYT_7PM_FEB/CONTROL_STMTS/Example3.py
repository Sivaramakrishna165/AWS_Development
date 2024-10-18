import time

n=int(input("Enter a number : "))

i=1
while i<=n:
    time.sleep(.2)
    print(i,end='\t')
    i=i+1
