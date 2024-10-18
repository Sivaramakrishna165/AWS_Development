



import os.path
import time

path="e:\\adv_super\\jdbc\\createtable.java"

if os.path.exists(path):
    print("Path is Existed ...")

    if os.path.isfile(path):
        f=open(path)
        data=f.read()
        
        for i in data:
            time.sleep(.1)
            print(i,end='')

        f.close()        
else:
    print("Sorry Path Not Existed ")
   
