class SuperA:
    def method1(self):
        print("Ins mtd-1 of SA")

class SubB(SuperA):
    def method1(self):
        super().method1()
        print("Ins mtd-2 of SB")

#calling
s=SubB()
s.method1()

#super( ).methodname([list of args])
