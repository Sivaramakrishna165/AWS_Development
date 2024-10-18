# global vs globals( )
# global vs nonlocal

# globals( ) -> dict  with global variables and their values
# d={'x':10}

x=10
def myFun():
    x=20
    print("x val is : ",x)
    d=globals()
    print("global x val : ",d['x'])
    print("global x val : ",globals()['x'])
    print("global x val : ",globals().get('x'))

#calling
myFun()
