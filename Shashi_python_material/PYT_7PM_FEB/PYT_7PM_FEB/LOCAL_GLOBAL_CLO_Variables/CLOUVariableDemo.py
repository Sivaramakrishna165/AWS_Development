z=30
def OuterFun():
    x=10
    def InnerFun():
        y=20
        print("From Inner Fun ")
        print("x val is :",x) #10
        print("y val is : ",y) #20
        print("z val is : ",z) #30
        print("=================")

    InnerFun()
    print("From OuterFun")
    print("x val is : ",x) #10
    #print("y val is :",y)  NE
    print("z val is : ",z) #30

#calling
OuterFun( )
