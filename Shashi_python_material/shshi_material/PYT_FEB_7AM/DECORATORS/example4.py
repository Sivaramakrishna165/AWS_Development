def Smart_Division(func):
    def wrapper(x,y):
        if y==0:
            print("Sorry V R N D By Zero....")
        else:
            func(x,y)
    return wrapper      

@Smart_Division #division=Smart_Division(division)
def division(x,y):
    z=x/y
    print("Result is : ",z)  

#calling
division(10,0)
