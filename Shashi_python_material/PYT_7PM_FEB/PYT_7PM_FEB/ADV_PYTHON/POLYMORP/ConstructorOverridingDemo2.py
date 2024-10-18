
class SuperA:
    def __init__(self):
        print("Def const of SA ")

class SubB(SuperA):
    def __init__(self):
        super().__init__()
        print("Def const of SB ")

''' calling '''
sb=SubB()

''' Syn: super().__init__([list of args]) '''
