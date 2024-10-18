
n=int(input("enter a number : "))

if n==1:
    print("One")
elif n==2:
    print("Two")
elif n==3:
    print("Three")
else:
    print("Invalid")


print("one") if n==1 else print("two") if n==2 else print("three") if n==3 else print("Invalid")


