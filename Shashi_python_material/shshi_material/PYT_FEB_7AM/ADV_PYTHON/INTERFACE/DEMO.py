
class
   - collection of non abstract methods
   
abstract class
    - collection of both abstract or non abstract mtd
    
Interface
    - collection of only abstract methods
    - Pure abstract class.

    class Test:
        def method1(self):
            pass

    ==================
    class Test(ABC):
        def method1(self):
            pass

        @abstractmethod
        def method2(self):
            pass
    ===================
    class Test(ABC):
        @abstractmethod
        def method2(self):
            pass
    


    




        
