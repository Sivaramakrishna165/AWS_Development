
class Biggest:
    def setData(self,x,y):
        self.x=x
        self.y=y

    def findBiggest(self):
        if self.x>self.y:
            print("biggest is : ",self.x)
        else:
            print("biggest is : ",self.y)

#calling
b=Biggest()
print("enter 2 numbers :")
b.setData(int(input()),int(input()))
b.findBiggest( )











