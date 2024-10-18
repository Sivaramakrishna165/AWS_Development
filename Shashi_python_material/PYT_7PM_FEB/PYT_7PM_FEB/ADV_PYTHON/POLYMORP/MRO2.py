
class A:
    pass

class B(A):
    pass

class C(B):
    pass

''' calling '''
lst=C.mro()
import time
for i in lst:
    time.sleep(1)
    print(i)
