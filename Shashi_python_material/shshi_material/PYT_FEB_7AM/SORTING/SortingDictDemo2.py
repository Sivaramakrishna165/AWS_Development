

#sorted(iterable,key=None,reverse=False) -> list
d={"c":"cnu","d":"dhanu","a":"amma","b":"brother"}
print("Dict : ",d)

lst=sorted( d.items() )
d2={}

import time
for t in lst:
    k,d=t
    d2.update({k:d})

print("Sorted dict : ")
print(d2)
    
    
    




