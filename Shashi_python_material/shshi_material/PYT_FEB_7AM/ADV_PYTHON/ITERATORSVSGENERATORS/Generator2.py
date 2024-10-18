
'''generator is an alternative way
    to defined class level iterator

    - defining generator is nothing but
    defining a function with yield keyword.

    - if any function which is defined with yeild keyword
    internally it works as generator object an iterable
    only. where we can loop through it. '''

def myFun():
    lst=["anu","aishu","cnu","mani"]
    index=0
    while index<len(lst):
        yield lst[index]
        index=index+1

    
m=myFun()
print("type is : ",type(m))

import time
for i in m:
    time.sleep(.1)
    print(i)











    
