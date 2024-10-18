from abc import ABC,abstractmethod

class Test(ABC):
    @abstractmethod
    def method1(self):
        pass

    @abstractmethod
    def method2(self):
        pass

class Testing(Test):
    def method1(self):
        print("OR mtd-1 of Test")

    def method2(self):
        print("OR mtd-2 of Test")

t=Testing()
t.method1()
t.method2()








