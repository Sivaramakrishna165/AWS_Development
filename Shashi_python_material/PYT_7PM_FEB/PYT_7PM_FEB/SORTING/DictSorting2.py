




#sorted(iterable,key=None,reverse=False) -> list
#D.keys( ) -> dict_keys | iterable
#D.values( ) -> dict_values | iterable
#D.items( ) -> dict_items | iterable
#D.update({k:d})

stu={"b":"balu","c":"cnu","d":"dhanu","a":"aishu"}
print("stu : ",stu)
lst=sorted(stu.items())
stu2={}

for t in lst:
    k,d=t
    stu2.update({k:d})

print("Sorted Dict : ")
print(stu2)
print("==========================")

