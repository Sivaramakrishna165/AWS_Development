
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

values=stu.values()
print("Values : ",values)

import time
for v in values:
    time.sleep(.2)
    print(v)












