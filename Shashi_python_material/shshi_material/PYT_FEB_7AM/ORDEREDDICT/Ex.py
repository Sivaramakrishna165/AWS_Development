import time

d=dict()
d.update({"sno":101})
d.update({"sname":"Raj"})
d.update({"scity":"hyd"})
print("Dict ; ",d)

for k1,d1 in d.items():
    time.sleep(.2)
    print(k1,d1,sep=" <<<>>> ")
print("================================")

import collections
od=collections.OrderedDict()

od.update({"sno":101})
od.update({"sname":"Raj"})
od.update({"scity":"hyd"})
print("Dict ; ",od)

for k1,d1 in od.items():
    time.sleep(.2)
    print(k1,d1,sep=" <<<>>> ")





