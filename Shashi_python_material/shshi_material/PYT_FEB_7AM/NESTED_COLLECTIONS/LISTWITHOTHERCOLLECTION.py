


import time
lst=[10,12.12,[11,22,33],
                          (1.1,2.2,3.3),
                          {"aaa","bbb","ccc"},
                          {"sno":101,"sname":"sai"} ]

print("Inner List  : ",lst[2])
print("2nd item in inner list : ",lst[2][1])

for i in lst[2]:
    time.sleep(.2)
    print(i)
print("==================")

print("Inner Dict : ",lst[5])
print("Name is : ",lst[5]['sname'])
print("Name is : ",lst[5].get('sname'))

for k,d in lst[5].items():
    time.sleep(.2)
    print(k,d,sep=' <<>> ')



print("Set : ",lst[4])
lst[4].add("ddd")
print("set : ",lst[4])








    
