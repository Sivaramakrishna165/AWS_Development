
''' Can i write more than  one except
                                     for a single try ?
Ans: yes '''

import sys

try:
    x=int( sys.argv[1] )
except ValueError:
    print("VE : Please Enter int input ")
except IndexError:
    print("IE : Please Enter at least one input ")
else:
    print("Given input is : ",x)





