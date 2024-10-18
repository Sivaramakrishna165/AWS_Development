




from abc import ABC,abstractmethod

class Sample(ABC):
    def method1(self):
        print("Non abstract mtd")

    @abstractmethod
    def method2(self):
        pass
