

import time
fname=input("Enter File name ")
f=None
try:
    f=open(fname,"r")
except FileNotFoundError:
    print("Sorry File Not Found")
else:
    data=f.read()
    for i in data:
        time.sleep(.1)
        print(i,end='')
finally:
    if f!=None:
        f.close()
        print("File is Closed ")
