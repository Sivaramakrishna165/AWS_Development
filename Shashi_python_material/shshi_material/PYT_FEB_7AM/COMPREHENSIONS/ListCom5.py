




lst=["anu","roja","cnu","nani","many","sunnY"]
print("List : ",lst)

lst2=[]
for i in lst:
    if len(i)==4:
        lst2.append(i)
print("lst2 : ",lst2)

print("===========================")
lst3=list( filter( lambda x: len(x)==4 , lst) )
print("Result is : ",lst3)
print("===========================")

lst4=[i for i in lst if len(i)==3]
print("Result is : ",lst4)









