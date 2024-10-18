
import time
import random

for i in range(1,11):
    time.sleep(.2)
    fd=random.randint(6,9)
    d=""
    for j in range(1,10):
        d=d+str(random.randint(0,9))
    mb=str(fd)+d
    print(mb)
