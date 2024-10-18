
#reduce( function, seq ) -> value
#From functools

import functools
r=functools.reduce( lambda x,y: x+y   , [1,2,3] )
print("Result is : ",r)
print("====================================")

'''
n=4
f=1
for i in range(1,n+1):
    f=f*i
print("Fact is : ",f) '''

f=functools.reduce( lambda x,y : x*y , [1,2,3,4,5] )
print("Fact is : ",f)















