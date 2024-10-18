



#L.copy() -> shallow copy
#copy() from copy module
#deepcopy() from copy module for deep copy

import copy
x=[10,[11,22],20]
y=copy.deepcopy(x)

print("x list : ",x)
print("y list : ",y)

print("After modification ")
x[0]=80
x[1][0]=99
print("x list :",x)
print("y list :",y)




