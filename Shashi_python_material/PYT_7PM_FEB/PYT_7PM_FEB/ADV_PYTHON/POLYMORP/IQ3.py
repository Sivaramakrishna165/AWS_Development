class A:
    def method1(self):
        print("A")

class B(A):
    def method1(self):
        print("B")

class C(B):
    def method1(self):
        super(B,self).method1()
        print("C")

''' calling '''
c=C()
c.method1()

