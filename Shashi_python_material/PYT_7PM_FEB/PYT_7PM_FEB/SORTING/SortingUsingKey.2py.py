




#sorted(iterable,key=None,reverse=False) -> list
lst=[("nani",23,6),("balu",52,8),("ramesh",32,10)]
print("List : ",lst)

lst=sorted(lst,key=lambda x:x[2],reverse=True)
print("Details : ",lst[1])
