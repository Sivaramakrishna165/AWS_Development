


''' break and continue
     these are used only in the looping stmt(s)

     break vs exit( )
'''

import time

for i in range(1,11):
    if i==6:
        break
    time.sleep(.2)
    print(i)

print("From outside of the loop")




