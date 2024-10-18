
lst=[10,20,30,40,50,60]
print("List : ",lst)

pos=int(input("Enter pos : "))

if pos<len(lst):
    item=lst[pos]
    print("Item : ",item)
else:
    print("Invalid Index ")
