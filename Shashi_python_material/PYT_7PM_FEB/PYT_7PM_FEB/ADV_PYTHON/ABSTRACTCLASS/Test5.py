




from abc import ABC,abstractmethod

class SuperA(ABC):
    @abstractmethod
    def method1(self):
        pass

class SubB(SuperA):
    def method1(self):
        print("OR mtd-1 of SA")

''' calling '''
#sa=SuperA( )
sb=SubB()
sb.method1()




        
    
