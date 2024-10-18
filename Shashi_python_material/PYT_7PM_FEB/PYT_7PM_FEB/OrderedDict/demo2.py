import time

stu=dict()
print("type is : ",type(stu))

stu.update({"sno":101})
stu.update({"sname":"sai"})
stu.update({"scity":"hyd"})
stu.update({"spin":500090})

for k,d in stu.items():
    time.sleep(1)
    print(k,d,sep=' >>> ')
print("=============================")

import collections
od=collections.OrderedDict()
print("type is : ",type(od))

od.update({"sno":101})
od.update({"sname":"sai"})
od.update({"scity":"hyd"})
od.update({"spin":500090})

for k,d in od.items():
    time.sleep(1)
    print(k,d,sep=' >>> ')













