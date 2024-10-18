
def greet():
    a="Hello"
    return a

def specialGreetings(func): #func is copy of greet
    m=func( ) #calling greet()
    n=m+" Dear "
    return n

#calling
c=greet()
print("Result of greet ? : ",c)

r=specialGreetings(greet)
print("Result of SGreetings ? : ",r)

