
class SuperA:
    def method1(self):
        print("Mtd-2 of SA")

class SubB(SuperA):
    pass

''' calling '''
sb=SubB()
sb.method1()
