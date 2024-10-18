




#reduce(function,seq) -> value from functools module

import functools
sn=functools.reduce(lambda x,y: x+y ,[1,2,3])
print("Sum of NN : ",sn)

f=functools.reduce(lambda x,y: x*y  ,[1,2,3,4] )
print("Fact : ",f)
