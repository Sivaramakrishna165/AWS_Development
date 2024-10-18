
def division(x,y):
    z=x/y
    print("Result is : ",z)

def Smart_Division(func): #func is copy division
    def wrapper(x,y):
        if y==0:
            print("SORRY V R N D BY ZERO ....")
        else:
            func(x,y)          
    return wrapper        

#calling
#division(10,0)
division=Smart_Division(division)
division(10,0)
