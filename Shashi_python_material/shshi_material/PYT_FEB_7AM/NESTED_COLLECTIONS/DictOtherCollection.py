import time

data= {
    "sno":101,
    "sname":"Ramesh",
    "qualifications":[ "Msc","BEd","LLB"],
    "address":{
                             "Hno":123,
                             "street":"1A/a",
                             "city":"Hyd",
                             "pin":500090
                         },
    "marks":( 40,50,60,70,78,30)
}

for k,d in data.items():
    if isinstance(d,dict):
        print(k)
        for k1,d1 in d.items():
            time.sleep(.2)
            print("    ",k1," ---> ",d1)
            
    elif isinstance(d,list):
        print(k)
        for i in d:
            time.sleep(.2)
            print("    ",i)

    elif isinstance(d,tuple):
        print(k)
        s=0
        for i in d:
            time.sleep(.1)
            print("    ",i)
            s=s+i
        print("=========")
        print("Sum is : ",s)

    else:
        print(k," ---> ",d)
            
        



        

''' Output:
sno   --> 101
sname -> Ramesh
qualifications :
    Msc
    BEd
    LLB
address:
   Hno : 123
   street : 1A/a
   city : Hyd
   pin : 500090
Marks:
   40
   50
   60
   70
   78
   30
=====
   xxx  '''
   


