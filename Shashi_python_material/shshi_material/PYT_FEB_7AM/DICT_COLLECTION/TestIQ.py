



#D.update({k:d})
#D.setdefault(k,d=None) -> default value for d is None
#D.fromkeys(iterable,value=None) -> dict

lstn=["sai","raj","ram"]
lstc=["Python","Django"]

import time
'''
D={}
for k,d in lstn,lstc:
    time.sleep(.2)    
    D.update({k:d})
print("Dict : ",D)
'''

#zip(iterable,iterable) -> zip object |  iterable
z=zip(lstn,lstc)
#dict(iterable) -> dict
d2=dict(z)
print("Dict : ",d2)






























