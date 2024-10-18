
class SuperA:
    def method1(self):
        print("Ins mtd-1 of SA")

class SubB(SuperA):
    pass

#calling
s=SubB()
s.method1()
