
class SuperA:
    @staticmethod
    def method1():
        print("static mtd-1 of SA")

class SubB(SuperA):
    def method2(self):
        self.method1()
        SubB.method1()
        SuperA.method1()
        print("Ins mtd-2 of SB")

''' calling '''
sb=SubB()
sb.method1()
sb.method2()
