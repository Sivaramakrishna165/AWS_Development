
x=10 #int
y=20 #int
z=x+y
print("Result is : ",z)
print("=================")

a="sai" #str
b="baba" #str
c=a+b
print("Result is : ",c)


class Java:
    def __init__(self):
        self.pages=200

    def __add__(self,other):
        return self.pages+other.pages

class Python:
    def __init__(self):
        self.pages=300

''' Calling '''
j=Java( )
p=Python()
print("Java Pages : ",j.pages)
print("Python Pages : ",p.pages)
tp=j+p
print("total Pages are : ",tp)

''' In Python For Every Operator there is method
is avaiable in Object class called Magic methods

Operator                           Method
+                                          __add__(self,other)
-                                          __sub__(self,other)
*                                         __mul__(self,other)
/                                         __div__(self,other)
//                                        __floordiv__(self,other)

>                                       __gt__(self,other)
>=                                    __ge__(self,other)
<                                       __lt__(self,other)
<=                                     __le__(self,other)
'''
















        








