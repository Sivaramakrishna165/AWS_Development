
class Test:
    def method1(self):
        self.x=10

#calling
t1=Test()
t1.method1()
t2=Test()
t2.method1()
print("t1 x : ",t1.x)
print("t2 x : ",t2.x)

t1.x=99
print("t1 x : ",t1.x)
print("t2 x : ",t2.x)
