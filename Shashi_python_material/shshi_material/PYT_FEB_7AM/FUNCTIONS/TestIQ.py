
def myFun(a,b,/,c,d,*,e,f):
    print("a : ",a)
    print("b : ",b)
    print("c : ",c)
    print("d : ",d)
    print("e : ",e)
    print("f : ",f)
    print("==============")

#calling 
myFun(10,20,30,40,e=50,f=70)
myFun(10,20,c=30,d=40,e=50,f=60)
