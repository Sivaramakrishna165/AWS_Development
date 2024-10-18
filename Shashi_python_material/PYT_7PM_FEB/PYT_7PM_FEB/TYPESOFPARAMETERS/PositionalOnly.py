

def myFun(*,name,age):
    print("Name is : ",name)
    print("Age is : ",age)
    print("==============")

''' calling '''
#myFun("james",22) TypeError

myFun(name="james",age=22)
myFun(age=23,name="ravi")
#myFun(name="jaya") TypeError
