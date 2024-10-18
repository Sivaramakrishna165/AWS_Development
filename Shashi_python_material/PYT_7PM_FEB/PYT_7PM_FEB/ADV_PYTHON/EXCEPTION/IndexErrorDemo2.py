#        0   1    2   3    4   5
lst=[10,20,30,40,50,60]
print("List : ",lst)

pos=int(input("Enter pos : ")) #3
try:
    item=lst[pos]
except IndexError:
    print("Sorry Invalid Index")
else:
    print("Item is : ",item)

