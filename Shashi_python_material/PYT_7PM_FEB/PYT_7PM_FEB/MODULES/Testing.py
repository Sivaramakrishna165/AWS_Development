
import mymodule
print(mymodule.lst)

import mymodule as mm
print(mm.lst)

from mymodule import lst
print(lst)

import mymodule,time
print(mymodule.lst)
time.sleep(1)

import mymodule as mm,time as t
print(mm.lst)
t.sleep(1)
============================
from modulename import members
from mymodule import *
from time import sleep




