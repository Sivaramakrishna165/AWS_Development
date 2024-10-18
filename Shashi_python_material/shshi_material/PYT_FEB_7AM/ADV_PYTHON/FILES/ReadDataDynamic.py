
import time

fname=input("Enter File Name : ")
f=None
try:
    f=open(fname,"r")
except FileNotFoundError:
    print("Sorry File Not Found .... :( ")
else:
    data=f.read()
    for i in data:
        time.sleep(.1)
        print(i,end='')
finally:
    try:
        f.close()
    except AttributeError:
        pass


