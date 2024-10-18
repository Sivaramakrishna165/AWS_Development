
def OuterFunc():
    def InnerFunc():
        x=10*2+30
        return x

    a=InnerFunc()
    return a

#calling
b=OuterFunc()
print("Result is : ",b)

''' Note-1:  If u want use the result of the innerfunction
inside of outerfunction then inner function need to
return the result

Note-2:If u want use the result of the inner function
outside of the outer function then outerfunction need
to return the result of the inner function. '''
