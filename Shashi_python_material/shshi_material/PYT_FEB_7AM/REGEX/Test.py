




'''  \d{1,2}-\w{1,3}-\d{2,4} '''

import re
import time

data='''ravi 12-Jan-98 manas 2-12-1999 madhu 22-3-99
sai 3-Mar-1998 nani 12-12-19'''

citr=re.finditer(".",data)
for m in citr:
    time.sleep(.2)
    print(m.group())




    

