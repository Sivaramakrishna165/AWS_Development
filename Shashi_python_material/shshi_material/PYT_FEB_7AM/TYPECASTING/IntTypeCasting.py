''' int type casting using int( ) '''

#float --> int
x=12.1212
y=int(x)                               
print(type(x)," ----> ",type(y))
print("x : ",x," ----> ","y : ",y)
print("=====================")

#complex -> int
x=(10+20j)
#y=int(x) TypeError : complex can't be converted int type.

#str -> int
x="120"
y=int(x)
print(type(x)," ----> ",type(y))
print("x : ",x," ----> ","y : ",y)
print("=====================")

#bool -> int   True--> 1 | False ->0
x=True
y=int(x)
print(type(x)," ----> ",type(y))
print("x : ",x," ----> ","y : ",y)
print("=====================")


















