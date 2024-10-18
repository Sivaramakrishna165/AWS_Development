
from abc import ABC,abstractmethod

'''
class Super(ABC):
    pass
s=Super()
'''

'''
class Super(ABC):
    def method1(self):
        pass
s=Super()
'''
'''
class Super(ABC):
    @abstractmethod
    def method1(self):
        pass
'''

class Super(ABC):
    @abstractmethod
    def method1(self):
        pass

    def method2(self):
        pass

s=Super()








