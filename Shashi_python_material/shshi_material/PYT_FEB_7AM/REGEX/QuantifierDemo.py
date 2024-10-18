



import re
import time

citr=re.finditer("a+","ab aac aaad aaaae")

for m in citr:
    time.sleep(.2)
    print("Match : ",m.group()," Index : ",m.start() )

'''Quantifier
     "a" --> Only a
     "a+"   --> atleast one a
     "a?"  ---> atmost one a
                          1-a or 0-a's considered as match

     "a*"  ---> 0-a's or any no.of.a's consider as match '''








     
