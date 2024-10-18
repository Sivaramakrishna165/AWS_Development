class A:
    def method1(self):
        print("Mtd-1 of A")

class B(A):
    def method1(self):
        print("Mtd-1 of B")

class C(B):
    def method1(self):
        a=A()
        a.method1()
        print("Mtd-1 of C")

#calling
c=C()
c.method1()
