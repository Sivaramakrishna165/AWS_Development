

def greet(name):    
    print("Hello ",name," Have a nice Day")

def DEC_Greeting(func): #func is copy of greet
    def wrapper(name):
        if name=="roja":
            print("Hello ",name," Have a good Day ")
        else:
            func(name)

    return wrapper

#calling
#greet("roja")
greet=DEC_Greeting(greet) #greet is copy of wrapper
greet("roja")

