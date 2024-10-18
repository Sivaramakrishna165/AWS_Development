




#[<exp> for var in iterable for var in iterable if test]
lstn=["Ram","Anu"]
lsti=["Pens","Books","Box"]

import time
sales=[(i,j) for i in lstn for j in lsti]
for t in sales:
    time.sleep(.2)
    print(t)

lst=["A","B","C"]
lstn=[1,2,3]

l=[i*j for i in lst for j in lstn if i=="B"]
for i in l:
    time.sleep(.2)
    print(i)






