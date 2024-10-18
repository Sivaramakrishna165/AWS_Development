
class A:
    pass

class B:
    pass

class C(A,B):
    def method1(self):
        super().method1()
        print("Mtd-1 of C")

''' calling '''
c=C()
c.method1()
