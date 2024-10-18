#D.keys() -> dict_keys | iterable
#D.values( ) -> dict_values | iterable

stu={"sno":101,"sname":"ramesh"}
print("student : ",stu)

''' Output:
sno -> 101
sname -> ramesh '''

keys=stu.keys()
for k in keys:
    print(k,"--->",stu[k])






