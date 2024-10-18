
''' complex type casting using
        complex(x)
            here x-rep real part
            where imag always rep with 0
            
        complex(x,y)
            x-real  | y-image
            in this case str with other combo's are
            not possible
'''
x=10
x=12.12
x="12.3"
x=True
y=complex(x)
print("Result is : ",y)





