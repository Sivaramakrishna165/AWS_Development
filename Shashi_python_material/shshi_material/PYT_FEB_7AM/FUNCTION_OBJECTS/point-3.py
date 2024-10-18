import time
def myFun():
    def stars():
        time.sleep(.2)
        for i in range(1,11):
            print("*",end=' ')

    stars()
    print("\n welcome ")
    stars()
    print("\n to ")
    stars()
    print("\n SssiT")
    stars()

#calling
#stars( ) NE
myFun()
