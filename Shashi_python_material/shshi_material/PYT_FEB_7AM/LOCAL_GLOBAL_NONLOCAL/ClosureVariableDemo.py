
z=30
def OuterFun():
    y=20
    def InnerFun():
        x=10
        print("Inf : x val is :",x)
        print("Inf : y val is : ",y)
        print("Inf : z val is : ",z)

    InnerFun()
    #print("Of : x val is : ",x) NE
    print("OF : y val is : ",y)
    print("OF : z val is : ",z)

#calling
OuterFun()
print("OOF z val is : ",z)


