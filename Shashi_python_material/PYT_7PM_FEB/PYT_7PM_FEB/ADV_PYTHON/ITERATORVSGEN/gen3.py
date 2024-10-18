import time

def myFun():
    yield "shashi"
    yield "james"
    yield "nani"
    yield "Somu"

m=myFun()
print("type is : ",type(m))
#print("Generator : ",m)

for i in m:
    time.sleep(1)
    print(i)
    
