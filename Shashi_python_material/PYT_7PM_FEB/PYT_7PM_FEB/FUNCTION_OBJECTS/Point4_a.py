
def OuterFunc():
    def InnerFunc():
        x=10*2+30
        return x

    a=InnerFunc()
    print("Result is : ",a)

#calling
OuterFunc()

''' Note-1:  If u want use the result of the innerfunction
inside of outerfunction then inner function need to
return the result '''
