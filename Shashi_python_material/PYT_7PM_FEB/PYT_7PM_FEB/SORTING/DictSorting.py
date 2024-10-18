




#sorted(iterable,key=None,reverse=False) -> list
#D.keys( ) -> dict_keys | iterable
#D.values( ) -> dict_values | iterable

stu={"b":"balu","c":"cnu","d":"dhanu","a":"aishu"}
print("stu : ",stu)

skeys=sorted(stu.keys())
svalues=sorted(stu.values())

#zip(iterable,iterable) -> zip | iterable
z=zip(skeys,svalues)
stu=dict(z)
print("sorted dict : \n ",stu)

print("==========================")

