
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

'''D.pop(k[,d]) -> d
if the specified k is existed then it will
remove that item and it will return the value of that
key.

if the specified k is not existed then it will return
d, if d is given else it will raise KeyError

D.popitem() -> tuple
D.clear( )'''


import time

stu={"sno":101,"sname":"ravi","scity":"hyd"}
print("Data is : ",stu)

t=stu.popitem()
print("Deleted item is : ",t)
print("Result : ",stu)













