#read() -> str

f=open("data3.txt","r")
data=f.read()
print(data)

import time
for i in data:
    time.sleep(.2)
    print(i,end='')

f.close()
