
class SuperA:
    def method1(self):
        print("Mtd-1 of SA")

class SubB(SuperA):
    def method1(self):
        print("Mtd-1 of SB ")

''' calling '''
sb=SubB()
sb.method1()
