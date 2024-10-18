from abc import abstractmethod,ABC

class SuperA(ABC):
    def method1(self):
        pass

class SubB(SuperA):
    pass

sb=SubB()
