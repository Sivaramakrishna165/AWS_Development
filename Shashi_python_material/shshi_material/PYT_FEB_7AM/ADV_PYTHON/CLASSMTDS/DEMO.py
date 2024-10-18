

class methods :
    - The methods which are defined
    with in the class with cls as first arguments and it should
    be defined by using @classmethod

    def method(self):  #instance mtd
        pass

    def method2(cls): #instance mtd | cls is same as self
        pass
    
    @classmethod
    def method3(cls):  #classmtd
        pass

    @classmethod
    def method4(self):  #classmtd | self as same as cls
        pass

    - Class methods can perform the operations
    only on static variables.

    - Every class methods must be referred by
    self or classname throughout the same class.

    - Every Class method must be referred by
    object reference or classname whenever u want
    access it from outside of the class.


    


    
