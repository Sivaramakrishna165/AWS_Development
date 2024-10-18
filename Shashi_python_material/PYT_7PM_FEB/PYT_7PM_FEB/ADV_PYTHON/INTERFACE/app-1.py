from abc import ABC,abstractmethod

class Test(ABC):
    @abstractmethod
    def method1(self):
        pass

class Testing(Test):
    def method1(self):
        print("OR mtd-1 of Test")

''' calling '''
t=Testing()
t.method1()

    
