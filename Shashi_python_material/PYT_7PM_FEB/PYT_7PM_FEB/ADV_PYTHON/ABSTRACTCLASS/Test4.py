




from abc import ABC,abstractmethod

class SuperA(ABC):
    @abstractmethod
    def method1(self):
        pass

class SubB(SuperA):
    pass

''' calling '''
s=SubB()


