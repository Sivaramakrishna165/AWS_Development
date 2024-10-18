
class SuperA:
    def method1(self):
        print("Ins mtd-1 of SA")

    @classmethod
    def method2(cls):
        print("cls mtd-2 of SA")
            
    @staticmethod
    def method3():
        print("static mtd-3 of SA")

class SubB(SuperA):
    pass

''' calling '''
sb=SubB()
sb.method1()

sb.method2()
SubB.method2()

sb.method3()
SubB.method3()




