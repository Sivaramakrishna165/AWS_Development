#thrid.py
#Aliasing For modules
#import modulename as aliasname

import mymodule as mm #Userdefined
import time as t 

for i in mm.lst:
    t.sleep(.2)
    print(i)
print("===============")

mm.greetings()
