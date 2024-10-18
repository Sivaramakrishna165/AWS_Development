import time

def myFun():
    def stars():        
        for i in range(1,11):
            time.sleep(.2)
            print("*",end=' ')

    stars()
    print("\n welcome \n")
    stars()
    print("\n to \n")
    stars()
    print("\n SSSIT \n")
    stars()            

#calling
#stars( ) NE
myFun()
            
