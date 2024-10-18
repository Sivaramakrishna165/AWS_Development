
x=10  #<class 'int'>
y=20  #<class 'int'>
z=x+y
print("sum is : ",z)
print("=================")

a="Sri" #<class 'str'>
b="Sai" #<class 'str'>
c=a+b
print("Result is : ",c)
print("==================")

class Python:
    def __init__(self):
        self.pages=400

    def __add__(self,other):
        return self.pages+other.pages        

class Java:
    def __init__(self):
        self.pages=500

#calling
p=Python()
j=Java()
np=p+j
print("Total Pages : ",np)

'''
+         __add__(self,other)
-          __sub__(self,other)
*         __mul__(self,other)
/         __div__(self,other)
//        __floordiv__(self,other)
%       __mod__(self,other)

>      __gt__(self,other)
>=   __ge__(self,other)

<      __lt__(self,other)
<=   __le__(self,other)
==   __eq__(self,other)
!=    __ne__(self,other)

.
.
'''














































