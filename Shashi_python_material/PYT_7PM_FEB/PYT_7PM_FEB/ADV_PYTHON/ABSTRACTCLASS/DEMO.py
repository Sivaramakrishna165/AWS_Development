
Non abstract method
   def method1(self):
       print("Hello")
       
Null body method ---> Non abstract method
                                    x <---
   def method2(self):
       pass
    
abstract method
   @abstractmethod
   def method3(self):
       pass

What is class ?
    - Collection of non abstract method
    Eg:  class Sample:
                def method1(self):
                    pass
    
What is abstract class.?
     - Collection of both abstract or non abstract mtds
     - Defining an abstract class is nothing but
     creating the sub class of class ABC 

     class Sample(ABC):
         def method1(self):
             pass

        @abstractmethod
        def method2(self):
            pass

    abstractmethod and ABC from abc module
        abc | abstract class module 





     
   



