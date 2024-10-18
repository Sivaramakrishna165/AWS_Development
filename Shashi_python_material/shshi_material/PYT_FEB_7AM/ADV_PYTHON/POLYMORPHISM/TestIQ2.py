import time
class A: pass
class B(A): pass
class C(B): pass

#calling
c=C( )

lst=C.mro()
for i in lst:
    time.sleep(.2)
    print(i)



    

