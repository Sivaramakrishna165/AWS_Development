
'''generator is an alternative way
    to defined class level iterator

    - defining generator is nothing but
    defining a function with yield keyword.

    - if any function which is defined with yeild keyword
    internally it works as generator object an iterable
    only. where we can loop through it. '''


def myrange(start,end,step=1):
    while start<=end:
        yield start
        start+=step

import time
for i in myrange(1,10,2):
    time.sleep(.4)
    print(i)














