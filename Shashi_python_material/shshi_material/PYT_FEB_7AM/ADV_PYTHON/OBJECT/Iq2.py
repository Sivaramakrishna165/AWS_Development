
class A:
    pass

class B(A):
    pass

class C(object):
    pass

print("A is subclass of object ? : ",issubclass(A,object))
print("B is subclass of A ? : ",issubclass(B,A))
print("B is subclass of object ? : ",issubclass(B,object))
print("C is subclass of object ? : ",issubclass(C,object))

'''
1.object is the super class for every class in Python

2.If any class is not inherited by other classes then
that class is the direct sub class of object.

3.If any class is inherited by other classes then
that class is indirect sub class of object '''
