
def OuterFun():
    y=20
    def InnerFun():
        nonlocal y
        y=y+20
        print("Inf y : ",y)

    InnerFun()

#calling
OuterFun()
