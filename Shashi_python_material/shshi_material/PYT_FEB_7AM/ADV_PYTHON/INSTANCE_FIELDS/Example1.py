class Test:
    def method1(self):
        x=10
        self.y=20
        print("Mtd-1 of Test")
        print("x val is : ",x)
        #print("y val is : ",y) NE
        print("y val is : ",self.y)
        print("=================")

'''Calling '''
t=Test()
t.method1()
print("From Outside of the class")
#print("y val is : ",y) NE
#print("y val is : ",self.y)
print("y val is : ",t.y)





