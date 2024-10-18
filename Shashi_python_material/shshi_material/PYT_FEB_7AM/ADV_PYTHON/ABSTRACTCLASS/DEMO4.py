from abc import abstractmethod,ABC

class SuperA(ABC):
    def method1(self):
        pass

    @abstractmethod
    def method2(self):
        pass

class SubB(SuperA):
    def method2(self):
        pass

sb=SubB()
