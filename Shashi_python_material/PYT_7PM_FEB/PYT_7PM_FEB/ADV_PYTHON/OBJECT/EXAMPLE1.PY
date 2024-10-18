




class A:
    pass

print("A is subclass of object ? : ",issubclass(A,object))

class B(A):
    pass

print("B is subcls of A ? : ",issubclass(B,A))
print("B is subcls of object ? : ",issubclass(B,object))

class C:
    pass

print("C is subcls of object ? : ",issubclass(C,object))





