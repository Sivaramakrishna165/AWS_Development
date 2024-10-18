
class SuperA:
    def __init__(self):
        print("Super class constructor ")

class SubB(SuperA):
    def __init__(self):
        super().__init__()
        print("Sub Class Constructor ")

#calling
s=SubB()

#super().__init__([arguments])
