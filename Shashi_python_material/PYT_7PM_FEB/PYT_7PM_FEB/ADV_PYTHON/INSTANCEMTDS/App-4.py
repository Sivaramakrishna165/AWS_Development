
class Biggest:
    def setData(self,x,y):
        self.x=x
        self.y=y

    def findBiggest(self):
        if self.x>self.y:
            print("Biggest is : ",self.x)
        else:
            print("biggest is : ",self.y)            

#calling
b=Biggest()
m=int(input("Enter a number"))
n=int(input("Enter b number "))
b.setData(m,n)
b.findBiggest()
