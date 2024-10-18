
''' Accept 2 numbers from the user
findout biggest in two '''

print("Enter 2 numbers ")
a,b=int(input( )), int(input()) #10 20

if a>b:
    print("a is big",a)
else:
    print("b is big",b)

print("a is big") if a>b else print("b is big")
