
class SuperA:
    def method1(self):
        print("Ins mtd-1 of SA")

class SubB:
    def method2(self):
        print("Ins mtd-2 of SB")
        sa=SuperA()
        sa.method1()

''' calling '''
sb=SubB()
sb.method2()
