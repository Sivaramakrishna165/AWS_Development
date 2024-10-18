
''' Can i handle any exception
by a single except ?
Ans: Yes, it is possible by
writing except without Exception Class Name
or except with Exception as a Class Name '''

import sys

try:
    x=int(sys.argv[1])
    y=int(sys.argv[2])
    z=x/y

except Exception as r :
    print("Sorry Dear ")
    print("Unable to process....")
    print("Reason is : ",r)

else:
    print("Result is : ",z)




    
