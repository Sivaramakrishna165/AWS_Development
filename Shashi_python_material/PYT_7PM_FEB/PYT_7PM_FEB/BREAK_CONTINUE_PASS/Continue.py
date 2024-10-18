
import time

for i in range(1,11):
    time.sleep(.5)
    if i in [3,7,9]:
        continue
    print("Hello ... ",i)
    print("My Dear Friend")
    print("==============")
    
