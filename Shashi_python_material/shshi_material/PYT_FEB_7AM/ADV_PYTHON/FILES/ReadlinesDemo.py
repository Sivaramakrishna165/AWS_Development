#read( ) -> str
#read(bytes) -> str
#readline( ) -> str
#readlines( ) -> list

import time

f=open("data3.txt","r")
lst=f.readlines()

for l in lst:
    time.sleep(.2)
    print(l,end='')

f.close()
