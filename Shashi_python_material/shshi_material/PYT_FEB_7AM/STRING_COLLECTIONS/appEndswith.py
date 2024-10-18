
#s.startswith(sub) -> bool
#s.endswith(sub) -> bool

import time

lst=['manasa',10,'mamathA',2.2,'samathA','sony','Bunny']

for i in lst:
    time.sleep(1)
    if isinstance(i,str):
        if i.endswith('a') or i.endswith('A'):
            print(i)
    
