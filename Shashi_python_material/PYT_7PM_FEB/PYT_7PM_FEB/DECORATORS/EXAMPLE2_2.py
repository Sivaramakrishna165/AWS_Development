def Smart_Division(func): #func is copy division
    def wrapper(x,y):
        if y==0:
            print("SORRY V R N D BY ZERO ....")
        else:
            func(x,y)          
    return wrapper

@Smart_Division   #division=Smart_Division(division)
def division(x,y):
    z=x/y
    print("Result is : ",z)

#calling
division(10,0)


@SQOFSQ
sq(2)

@DEC_Split
@DEC_upper
def myData():
    s="welcome to python world"












