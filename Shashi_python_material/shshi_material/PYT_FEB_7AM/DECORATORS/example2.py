

def greet(name):
    print("Hello ",name," Have a nice day ")

def DEC_Greet(func): #func is copy of greet
    def wrapper(name):
        if name=="roja":
            print("Hello ",name," Have a GOOD day ")
        else:
            func(name)

    return wrapper

#calling
greet=DEC_Greet(greet)  #shashi is copy of wrapper
greet("roja") #calling wrapper()


