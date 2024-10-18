
def myFun():
    print("Hello")

''' calling 
function name itself acts as reference variable
it is refered to the function object by holding its
hashcode '''

print(" type is : ", type(myFun) )
print("Hcode is : \n ",myFun )
myFun()
print("==============================")

x=myFun #ref.copy
print("type is : ",type(x))
print("Hcode is : \n ",x)
x()









