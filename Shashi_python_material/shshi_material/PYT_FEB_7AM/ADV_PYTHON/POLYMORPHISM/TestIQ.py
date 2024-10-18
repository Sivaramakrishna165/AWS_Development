class A:
    pass

class B:
    def method1(self):
        print("Mtd-1 B")

class C(A,B):
    def method1(self):
        super().method1()
        print("Mtd-1 C")

#calling
c=C()
c.method1()
