
def myCalc(x,y):
    a=x+y
    s=x-y
    m=x*y
    return a,s,m
    

#calling
t=myCalc(10,2)
print("Result is : ",t)
print("sub is : ",t[1])
print("Mul is : ",t[2])

