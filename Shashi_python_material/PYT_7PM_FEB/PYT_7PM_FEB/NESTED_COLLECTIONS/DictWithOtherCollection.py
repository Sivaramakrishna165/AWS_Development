import time

stu={
    "Sno":101,
    "Sname":"Ramesh",
    "Qualifications":("Msc","BEd"),
    "Address":{"hno":"1-2-3","city":"hyd","pin":500090},
    "Marks":[40,50,60,70,80,40]
    }

for k,d in stu.items():
    time.sleep(1)
    if isinstance(d,dict):
        print(k)
        for k1,d1 in d.items():
            time.sleep(.2)
            print("    ",k1," : ",d1)

    elif isinstance(d,list):
        print(k)
        s=0
        for i in d:
            s=s+i
            time.sleep(.2)
            print("    ",i)
        print("========")
        print("total : ",s)

    elif isinstance(d,tuple):
        print(k)
        for i in d:
            time.sleep(.2)
            print("    ",i)

    else:
        time.sleep(1)
        print(k," : ",d)

            
        



'''Output:
sno : 101
sname : Ramesh
Qualifications:
    Msc
    BEd
Address:
    Hno : 1-2-3
    city : hyd
    pin : 500090
Marks:
   40
   50
   60
   70
   80
   40
====
   xxx   '''
   
