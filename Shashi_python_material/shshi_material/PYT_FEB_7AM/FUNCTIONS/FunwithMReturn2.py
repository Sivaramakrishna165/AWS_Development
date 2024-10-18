#define
def myCalc(a,b):
    add=a+b
    sub=a-b
    mul=a*b
    return add,sub,mul

#call
t=myCalc(10,2) #here t is acts as tuple  t=12,8,20
print("Result is : ",t)
print("Add is :",t[0])
print("Sub is : ",t[1])
print("Mul is : ",t[2])

