
class Test:
    def method1(self):
        self.x=10
        print("mtd-1 x : ",self.x)

    def method2(self):
        print("mtd-2 x :",self.x)

#calling
t=Test()
t.method2()
t.method1()

print("From outside of cls")
print("x val is : ",t.x)
