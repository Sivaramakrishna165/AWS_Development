




import re
import time

data="an apple a day keeps a doctor away"

citr=re.finditer(r"\b[a-zA-Z]{5}\b",data)

for m in citr:
    time.sleep(.2)
    print(m.group())
