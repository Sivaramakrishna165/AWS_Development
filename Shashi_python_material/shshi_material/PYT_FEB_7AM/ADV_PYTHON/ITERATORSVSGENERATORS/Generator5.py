
'''generator is an alternative way
    to defined class level iterator

    - defining generator is nothing but
    defining a function with yield keyword.

    - if any function which is defined with yeild keyword
    internally it works as generator object an iterable
    only. where we can loop through it. '''

import time
import sys

def myFun():
    lst=[i for i in range(1,501)]
    print("Type is : ",type(lst))
    print("size is : ",sys.getsizeof(lst))
    print("==========================")
    
def myFun2():
    t=(i for i in range(1,501))
    print("Type is : ",type(t))
    print("size is : ",sys.getsizeof(t))

myFun()
time.sleep(2)
myFun2()



    
    













