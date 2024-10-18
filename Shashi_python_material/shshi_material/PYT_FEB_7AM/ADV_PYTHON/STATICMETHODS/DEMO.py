
static methods:
    - The methods which are defined
    with in the class without self or cls
    and it should be defined by using
    @staticmethod

    def method1(self):  #instance mtd
        pass

    @classmethod
    def method2(cls):  #classmtd
        pass

    @staticmethod
    def method3(): #static method | utility mtd
        pass

* Every static method must be referred by
self or classname throughout the same class.

* Every static method must be referred by
classname or object reference whenever u want
access it from outside of the class.











    
