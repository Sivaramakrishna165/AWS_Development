#mainprg2.py


#import mainpkg8am.subpkg8am.sssit
from mainpkg8am.subpkg8am.sssit import *
import time

#for k,d in mainpkg8am.subpkg8am.sssit.courses.items():
for k,d in courses.items():
    time.sleep(.2)
    print(k,d,sep=' >>>> ')
