





''' Can i handle more than one exception
by a single except ?
Ans : yes '''

import sys

try:
    x=int(sys.argv[1])

except (ValueError,IndexError):
    print("VE | IE : Please Enter an Integer input ...")

else:
    print("Given value is : ",x)













    
