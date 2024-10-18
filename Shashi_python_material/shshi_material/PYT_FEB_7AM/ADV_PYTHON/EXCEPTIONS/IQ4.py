



''' Can i handle Any exception by a single except ?
Ans : Yes, Possible by using exception without
Exception or except with Exception'''

import sys

try:
    x=int(sys.argv[1])
    y=int(sys.argv[2])
    z=x/y
    
except Exception as e:
    print("GE : Sorry Unable to Continue....")
    print("Reason : ",e)
    
else:
    print("Result is : ",z)




    
    

    


    
    






    
