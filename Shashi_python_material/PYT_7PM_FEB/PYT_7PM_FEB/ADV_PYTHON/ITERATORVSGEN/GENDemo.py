
''' generator is an alternative way to define
                         our own iterator

    * Defining the gen is nothing but define a funtion
    with yield keyword.

    * If any function which defined with yield keyword
    that function return a generator object '''

def myFun():
    yield "shashi"

g=myFun()
print("Type is : ",type(g))






      
