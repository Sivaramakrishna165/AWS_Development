
class SuperA:
    @staticmethod
    def method1():
        print("static mtd-1 of SA")

class SubB(SuperA):
    def method2(self):
        self.method1()
        SubB.method1()
        SuperA.method1()
        sa=SuperA()
        sa.method1()
        print("Int mtd-2 of SB")

#calling
sb=SubB()
sb.method2()
