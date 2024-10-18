import time
class A:
    pass

class B:
    pass

class C(A,B):
    pass

#calling
c=C( )
lst=C.mro()

for i in lst:
    time.sleep(.2)
    print(i)
