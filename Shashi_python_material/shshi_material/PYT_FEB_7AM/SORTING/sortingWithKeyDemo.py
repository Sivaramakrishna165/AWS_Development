



#L.sort(key=None,reverse=False)
#sorted(iterable,key=None,reverse=False) -> list

lst=[("manas",32,40),("james",12,34),("anu",22,22)]
print("List : ",lst)

print(" ")
ln=sorted(lst,key=lambda x: x[0] ,reverse=False)
print("Sorted Based On Names ")
print(ln)

print(" ")
la=sorted(lst,key=lambda x:x[1])
print("Sorted Based on Age ")
print(la)

lst=sorted(lst,key=lambda x:x[2],reverse=True)
print("Result is : ",lst[1])





