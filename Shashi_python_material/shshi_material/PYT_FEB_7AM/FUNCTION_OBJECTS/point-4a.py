
def OuterFun():
    def InnerFun():
        x=10+20*3
        return x

    r=InnerFun()
    print("Result is : ",r)

#calling
OuterFun()
'''1.If u want use the result of the inner function inside
of the outer function then inner function
need to return the result '''
