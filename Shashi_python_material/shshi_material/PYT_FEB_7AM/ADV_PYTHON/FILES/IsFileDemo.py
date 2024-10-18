import time
from os import path

p="e:\\adv_super\\jdbc\\createtable.java"

if path.exists(p):
    if path.isfile(p):
        print("It is a File : ")
        print("======================")
        with open(p) as f:
            data=f.read()
            for i in data:
                time.sleep(.2)
                print(i,end='')            
    else:
        print("Sorry It is not File ")
else:
    print("Sorry Oath is Not Existed ")



