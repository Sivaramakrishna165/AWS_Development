








''' {<exp> for variable in iterable if test} '''

d={i:i for i in range(1,4)}
print("type is : ",type(d))
print("Dict : ",d)
print("===========================")


d2={i:i*i for i in range(1,4)}
print("Result is : ",d2)
print("===========================")

import math
d3={i:math.factorial(i) for i in range(1,6) if i in [1,3,4]}
print("Result is : ",d3)
























