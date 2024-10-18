
''' complex type casting
     complex(x) -> complex
         x-rep real part, where imag always remains 0j
         
     complex(x,y) -> complex
        x-rep real part, where y-rep image part
        str with other types are not supported '''

x=123
x=12.12
x="123"
x=True
x=False
y=complex(x)
print("Result is : ",y)
print("==============================")

a=123
b=12.12
c=True
d=False
e="123"

s=complex(e,a)
print("Result is : ",s)














