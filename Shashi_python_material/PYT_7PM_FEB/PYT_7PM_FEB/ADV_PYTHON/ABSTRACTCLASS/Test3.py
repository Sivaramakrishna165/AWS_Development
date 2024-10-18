




from abc import ABC,abstractmethod

class Sample(ABC):
    def method1(self):
        pass

    @abstractmethod
    def method2(self):
        pass

''' Calling '''
s=Sample()
