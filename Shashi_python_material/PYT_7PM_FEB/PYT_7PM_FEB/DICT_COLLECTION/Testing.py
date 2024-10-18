
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

import time

stu={"sno":101,"sname":"ravi","scity":"hyd"}
print("Data is : ",stu)

no=stu['sno']
print("no is : ",no)

''' App-1
keys=stu.keys()  #[sno,sname,scity]
for k in keys:
    time.sleep(.2)
    print(k," -----> ",stu[k])
'''

''' App-2
lst=stu.items() #[(sno,101),(sname,ravi),()]
for t in lst:
    time.sleep(1)
    k=t[0]
    d=t[1]
    print(k,d,sep=" >>>> ")
'''

''' App-3
lst=stu.items()
for t in lst:
    time.sleep(1)
    k,d=t
    print(k,d,sep=" <<<< ")
'''

#lst=stu.items() [(sno,101),(sname,ravi),()]

for k,d in stu.items():
    time.sleep(.2)
    print(k,d,sep=" <<<>>> ")
    
    








    
    














    









