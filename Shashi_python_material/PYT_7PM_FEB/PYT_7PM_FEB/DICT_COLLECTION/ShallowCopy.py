
#D.update({k:d})
#D.setdefault(k[,d])
#D.fromkeys(iterable,value=None)
#zip()

#how to convert other collection to dict
#how to convert string to dict collection

#D.keys( ) -> dict_keys | iterable
#D.values( ) -> dict_values | iterable
#D.items( ) -> dict_items | iterable

#D.copy() -> shallow copy of dict

#D.get(k[,d]) -> d

import time

stu={"sno":101,"sname":"ravi","scity":"hyd"}
print("Data is : ",stu)

stu2=stu.copy()
print("Result is : ",stu2)

stu.update({"spin":500090})
print("stu : ",stu)
print("stu2 : ",stu2)









