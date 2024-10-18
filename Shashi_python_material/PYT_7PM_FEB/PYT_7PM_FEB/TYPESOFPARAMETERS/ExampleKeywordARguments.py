
def myFun(name,age):
    print("Name is : ",name)
    print("Age is : ",age)
    print("==============")

''' calling '''
myFun(name="lilly",age=23)
myFun(age=22,name="Roja")
#myFun(name="James") TypeError

myFun("James",age=99)
#myFun(name="Jaya",56) SyntaxError

