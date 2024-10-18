
import time

def myRange(start,end):
    while start<=end:
        yield start
        start=start+1

#calling
for i in myRange(1,10):
    time.sleep(.2)
    print(i)
