
def myFun(name,age):
    print("Name is : ",name)
    print("Age is : ",age)
    print("====================")

#calling
myFun(name="Roja",age=22)
myFun(age=23,name="Sudha")
#myFun(name="Rajesh") TypeError

myFun("Rajesh",age=33)
#myFun(age=23,"Nani") SyntaxError
