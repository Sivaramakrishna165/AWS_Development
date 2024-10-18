




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable if test)
#Syn: { <exp> for variable in iterable  if test }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

d={i:i for i in range(1,4)}
print("type is : ",type(d))
print("dict : ",d)
print("====================")

d2={i:i*i for i in range(1,4)}
print("Dict : ",d2)
print("=====================")

import math
d3={i:math.factorial(i) for i in range(1,6) if i in [1,3,5]}
print("Dict : ",d3)






















      





