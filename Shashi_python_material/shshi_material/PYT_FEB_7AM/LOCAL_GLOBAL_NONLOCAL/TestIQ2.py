

#globals() -> dict with global variables
#{'x':20}

x=20

def myFun():    
    x=30
    print("myFun : ",x)
    d=globals()
    print("global x : ",d['x'])
    print("global x : ",globals()['x'])
    print("global x : ",globals().get('x'))
    print("global x : ",d.get('x'))
    

#calling
myFun()

