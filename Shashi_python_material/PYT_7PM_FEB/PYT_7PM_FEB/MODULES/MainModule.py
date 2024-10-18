
#MainModule.py

import time
def stars( ):
    for i in range(1,11):
        time.sleep(.2)
        print("*",end=' ')

    print("\n Have a nice Day")
    print("==================")

'''Calling '''
#print("type is : ",type(__name__))
#print("value of __name__ is  : ",__name__)

if __name__=='__main__':
    stars()

'''Note: if the execution is started from mainmodule
then calling of the stars( ) should be implicit by chance
if the execution is started from outside of mainmodule
then calling of the stars( ) should be explicit ...

*** to know from the where execution process
is started then we have to use predefined variable of
type class str ie.__name__

** the value of __name__ is '__main__' if the execution
of the program is started from mainmodule. If the
execution of the program is started from imported
module or from outside of the module then
value of __name__ is other than __main__ | imported
modulename.




'''






