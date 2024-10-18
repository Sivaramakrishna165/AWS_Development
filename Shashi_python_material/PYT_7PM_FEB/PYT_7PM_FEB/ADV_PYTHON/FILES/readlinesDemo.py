#read( ) -> str
#read(bytes) -> str
#readline( ) -> str
#readlines( ) -> list

import time

f=open("data3.txt","r")
lst=f.readlines()

for i in lst:
    time.sleep(.2)
    print(i,end='')



