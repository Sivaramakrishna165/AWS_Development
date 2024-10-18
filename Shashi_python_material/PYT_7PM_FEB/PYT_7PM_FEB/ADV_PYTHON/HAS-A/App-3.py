
class SuperA:
    @staticmethod
    def method1():
        print("static mtd-1 of SA")

class SubB:
    def method2(self):
        print("Ins mtd-2 of SB")
        sa=SuperA()
        sa.method1()
        SuperA.method1()

''' calling '''
sb=SubB()
sb.method2()
