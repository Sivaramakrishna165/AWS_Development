
''' bool type casting using bool( ) -> bool '''
x=1
y=bool(x)
print(type(x)," ----> ",type(y) )
print(x," -----> ",y)
print("=====================")

x=0.0
y=bool(x)
print(type(x)," ----> ",type(y) )
print(x," -----> ",y)
print("=====================")

x=(0+0.0j)
y=bool(x)
print(type(x)," ----> ",type(y) )
print(x," -----> ",y)
print("=====================")

x=""
y=bool(x)
print(type(x)," ----> ",type(y) )
print(x," -----> ",y)
print("=====================")







