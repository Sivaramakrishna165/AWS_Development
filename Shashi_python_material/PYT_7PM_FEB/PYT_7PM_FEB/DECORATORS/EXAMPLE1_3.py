

def DEC_Greeting(func): #func is copy of greet
    def wrapper(name):
        if name=="roja":
            print("Hello ",name," Have a good Day ")
        else:
            func(name)

    return wrapper

@DEC_Greeting #greet=DEC_Greeting(greet)
def greet(name):    
    print("Hello ",name," Have a nice Day")

#calling
greet("roja")




