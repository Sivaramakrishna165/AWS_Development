#alias names to the module
#syn : import modulename as aliasname

import mymodule as mm
import time as t

print("List : ",mm.lst)

for i in mm.lst:
    t.sleep(.2)
    print(i)

print("====================")
mm.myFun()
