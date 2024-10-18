
''' Can i handle more than one
exception by a single except ?
Ans : Yes '''

import sys

try:
    x=int(sys.argv[1])

except (IndexError,ValueError) :
    print("IE | VE : Please Enter an int input....")

else:
    print("Given number is : ",x)
