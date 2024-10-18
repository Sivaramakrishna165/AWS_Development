
'''generator is an alternative way
    to defined class level iterator

    - defining generator is nothing but
    defining a function with yield keyword.

    - if any function which is defined with yeild keyword
    internally it works as generator object an iterable
    only. where we can loop through it. '''

import time

lst=[i for i in range(1,501)]
print("type is : ",type(lst))
print("List : ",lst)
print("=====================")

time.sleep(1)
t=(i for i in range(1,501))
print("type is : ",type(t))
for i in t:
    print(i)












