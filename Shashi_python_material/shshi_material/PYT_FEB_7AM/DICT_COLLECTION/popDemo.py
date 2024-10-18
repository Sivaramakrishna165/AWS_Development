
#D.popitem() -> tuple
#D.pop(k[,d]) -> d

stu={"sno":101,"sname":"ramesh"}
print("student : ",stu)

item=stu.pop("sname")
print("Value of deleted key : ",item)
print("student : ",stu)

item=stu.pop("sname","xxx")
print("value of deleted key : ",item)

stu.pop("sname")
