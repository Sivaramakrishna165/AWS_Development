
def greet():
    a="Hello"
    return a

def SpecialGreet(func): #func is copy of greet
    x=func( ) #calling greet()
    y=x+" My Dear"
    return y

#calling
r=SpecialGreet( greet )
print("Result is : ",r)




