
#D.update({k:d})
#D.setdefault(k[,d])
#D.fromkeys(iterable,value=None)
#zip()

#how to convert other collection to dict
#how to convert string to dict collection

#D.keys( ) -> dict_keys | iterable
#D.values( ) -> dict_values | iterable
#D.items( ) -> dict_items | iterable

stu={"sno":101,"sname":"ravi","scity":"hyd"}
print("Type is : ",type(stu))
print("Data is : ",stu)

keys=stu.keys()
print("type is : ",type(keys))

import time
print("Keys : ",keys)
for k in keys:
    time.sleep(1)
    print(k)














