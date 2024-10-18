
def myFun(x):
    x[1]=99
    print("Result is : ",x)

#calling
lst=[10,20,30]
myFun(lst)
print("From outside of the fun")
print("List : ",lst)
