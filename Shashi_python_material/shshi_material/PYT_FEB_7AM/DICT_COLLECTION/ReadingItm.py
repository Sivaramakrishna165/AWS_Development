#D.keys() -> dict_keys | iterable
#D.values( ) -> dict_values | iterable
#D.items() -> dict_items | [(),()]

stu={"sno":101,"sname":"ramesh","scity":"hyd"}
print("student : ",stu)

items=stu.items()
print("Type is : ",type(items))
print("Items : ",items)
print("=============")


import time
'''
for t in items:
    time.sleep(.2)
    print(t[0],"--->",t[1])
print("=============")
'''

'''
for t in items:
    time.sleep(.2)
    k,d=t
    print(k,"--->",d)
'''

'''
for k,d in items:
    time.sleep(.2)
    print(k,d,sep=">>>")
'''

for k,d in stu.items():
    time.sleep(.2)
    print(k,d,sep=' <<<>>> ')



























    
    





