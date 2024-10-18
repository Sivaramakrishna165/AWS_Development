
def OuterFun():
    def InnerFun():
        x=10+20*3
        return x

    y=InnerFun()
    return y
    

#calling
r=OuterFun()
print("Result is : ",r)

'''1.If u want use the result of the inner function inside
of the outer function then inner function
need to return the result

2.if u want use the result of the inner function outside
of the outer function then outer function
need to return the result of inner func.'''




