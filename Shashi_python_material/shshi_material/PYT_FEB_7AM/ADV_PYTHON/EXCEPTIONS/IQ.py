

''' Can i write more than one except
for single try ?
Ans : yes '''

import sys

try:
    x=int(sys.argv[1])

except ValueError:
    print("VE : Please Enter integer input .... :( ")

except IndexError:
    print("IE : please Enter atleast 1 input ... :( ")

else:
    print("Given value : ",x)


    
