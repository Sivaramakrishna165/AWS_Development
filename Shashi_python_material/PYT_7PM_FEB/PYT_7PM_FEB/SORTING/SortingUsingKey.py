




#sorted(iterable,key=None,reverse=False) -> list
lst=[("nani",23),("balu",52),("ramesh",32)]
print("List : ",lst)

lst=sorted(lst,key=lambda x: x[0])
print("Sorted List Based Name")
print(lst)
print("==========================")

lst=sorted(lst,key=lambda x: x[1],reverse=True)
print("Sorted List Based On Age : ")
print(lst)


