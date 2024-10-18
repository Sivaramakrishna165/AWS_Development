
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
'''
D.get(k[,d]) -> default value for d is None
   if the specified k is existed then it will
   return value of that key.

   if the specified k is not existed then it will
   return d, if d is given else it will return None '''

import time

stu={"sno":101,"sname":"ravi","scity":"hyd"}
print("Data is : ",stu)
name=stu['sname']
print("Name is : ",name)
print("===================")

n=stu.get("sname1","James")
print("Name is : ",n)












