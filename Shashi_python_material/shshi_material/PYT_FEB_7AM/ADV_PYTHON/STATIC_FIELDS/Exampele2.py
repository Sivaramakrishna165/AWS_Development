
class Test:
    x=10 #static

    def method1(self):
        print("mtd-1 of test")
        #print("x val is : ",x) NE
        print("x val is : ",self.x)
        print("x val is : ",Test.x)
        

#calling
t=Test( )
t.method1()
