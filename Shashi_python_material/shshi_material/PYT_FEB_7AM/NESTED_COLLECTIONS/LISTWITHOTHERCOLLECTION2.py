


import time
lst=[ [11,22,33], (1.1,2.2,3.3),
         {"aaa","bbb","ccc"},
         {"sno":101,"sname":"sai","scity":"hyd"} ]

for i in lst:
    time.sleep(1)
    print("type is : ",type(i))
    print("Data is : ",i)
    print("===============")

    if isinstance(i,dict):
        for k,d in i.items():
            time.sleep(.2)
            print(k,d,sep=' <<>> ')
    else:
        for j in i:
            time.sleep(.2)
            print(j)


            




