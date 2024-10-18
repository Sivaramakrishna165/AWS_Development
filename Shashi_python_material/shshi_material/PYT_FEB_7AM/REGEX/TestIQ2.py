


import time
import re

citr=re.finditer("m\w\w","mom mam anu mad sri cnu")
print(citr)

for m in citr:
    time.sleep(1)
    print(m)
    print("Match : ",m.group())
    print("Found @ : ",m.start())
    print("===================")

    




