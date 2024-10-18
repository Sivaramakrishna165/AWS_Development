class Test:
    def method1(self):
        x=10
        self.y=20
        print("Mtd-1 of Test")
        print("x val is : ",x)
        print("y val is : ",self.y)
        print("="*20)

    def method2(self):
        print("Mtd-2 of Test")
        #print("x val is : ",x)
        print("y val is : ",self.y)
        print("="*20)

#calling
t=Test()
t.method1()
t.method2()
print("From Outside of the class")
print("y val is : ",t.y)


