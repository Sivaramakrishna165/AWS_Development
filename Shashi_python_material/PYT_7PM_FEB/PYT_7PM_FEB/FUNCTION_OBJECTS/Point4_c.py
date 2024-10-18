
def OuterFunc():
    def InnerFunc():
        x=10*2+30
        return x

    return InnerFunc

#calling
a=OuterFunc()   #a is the copy InnerFun
r=a()  #InnerFun()
print("Result is : ",r)



''' Note-1:  If u want use the result of the innerfunction
inside of outerfunction then inner function need to
return the result

Note-2:If u want use the result of the inner function
outside of the outer function then outerfunction need
to return the result of the inner function.

Note-3: if u want use the inner function from outside
of the outerfunction then outerfunction need to
return innerfun.

'''



