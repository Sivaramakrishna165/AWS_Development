





''' (<exp> for variable in iterable if test) '''
t=(i for i in range(1,11))
print("Type is : ",type(t))
t=tuple(t)
print("Result is : ",t)
print("===========================")

t=tuple(i*i for i in range(1,11) if i%2==0)
print("Result is : ",t)









