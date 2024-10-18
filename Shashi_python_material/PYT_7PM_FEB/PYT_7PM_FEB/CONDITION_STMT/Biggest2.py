
''' Accept 2 numbers from the user
findout biggest in two '''

a=int( input("enter a number") )
b=int( input("enter b number ") )

if a>b:
    print("Biggest is : ",a)
else:
    print("biggest is : ",b)

print("Biggest is :",a) if a>b else print("Biggest is :",b)
