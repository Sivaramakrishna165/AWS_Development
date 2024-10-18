
''' break and continue
      unconditional control statement
      only in the looping statement(s)

      break vs exit '''

import time
import sys

for i in range(1,11):    
    time.sleep(.3)
    if i==6:
        #break
        sys.exit()
    print(i)

print("Have a nice Day ")






