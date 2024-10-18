
non abstract method
   - method which is having body and
                                     implementation.

     def method1(self):
         print("Hellooooooo")
                                     
null body method
     - method which is having body without implementation

      def method1(self):
          pass
     
abstract method
    - method which is not having body and it should
    be defined with @abstractmethod

    @abstractmethod
    def method1(self):
        pass

What is a class ?
    - collection of non abstract methods

    class Sample:
        def method1(self):
            pass                
        def method2(self):
            pass
        
What is an abstract class ?
    - Collection of both abstract or non abstract mtds

    from abc import ABC,abstractmethod
    class Sample(ABC):
        def method1(self):
            pass
        
        @abstractmethod
        def method2(self):
            pass
    

















