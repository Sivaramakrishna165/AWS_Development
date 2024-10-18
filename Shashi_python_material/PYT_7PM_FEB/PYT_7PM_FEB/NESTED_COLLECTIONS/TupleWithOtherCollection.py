


t=( [10,20,30],(1.1,2.2,3.3),{"aaa","bbb","ccc"},
            {"sno":101,"sname":"ramesh","scity":"hyd"} )

import time

for i in t:
    if isinstance(i,dict):
        print("Dict : ",i)
        for k,d in i.items():
            time.sleep(.2)
            print(k,d,sep=" <<< >>> ")
            
    elif isinstance(i,tuple):
        time.sleep(2)
        print("Tuple : ",i)
        for j in i:
            time.sleep(.2)
            print(j)

