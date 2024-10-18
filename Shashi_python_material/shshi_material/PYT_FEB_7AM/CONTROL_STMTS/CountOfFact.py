
n=int( input("Enter a number : ") )

cnf=0

for i in range(1,n+1):
    if n%i==0:
        print(i)
        cnf=cnf+1

print("No.of.Fact : ",cnf)
