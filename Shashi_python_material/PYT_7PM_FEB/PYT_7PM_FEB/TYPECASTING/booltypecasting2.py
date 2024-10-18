''' bool True | False
   Non boolean False
         0 | 0.0 | 0+0j | "" | None | '''

x=0
x=0.0
x=0+0j
x=""

x=None
x=[]
x=()
x=set()
x=dict( )

y=bool(x)
print("Result is : ",y)
