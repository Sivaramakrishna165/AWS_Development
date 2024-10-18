import time

n=int( input("Enter a number ") )

i=1
while i<=n:
    time.sleep(.1)
    print(i,end=' ')
    i=i+1
