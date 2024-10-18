
def myFun(*,name,age):
    print("Name is : ",name)
    print("age is : ",age)
    print("===============")

#calling
myFun(name="Roja",age=23)
myFun(age=23,name="Sunny")
myFun("Sunny",22)
    
