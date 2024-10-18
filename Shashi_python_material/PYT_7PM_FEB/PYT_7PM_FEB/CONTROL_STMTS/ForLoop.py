''' Iterables are :
     str | list | tuple | set | dict | range
     cursor | file | dict_keys | dict_values
     dict_items | callable_iterator | map | zip | filter .... '''

''' for <variable> in <iterable>:
    .... stmt(s) '''

import time
lst=[10,20,30,"shashi",2.2,None,"Kumar"]
print("List : ",lst)

for i in lst:
    time.sleep(1)
    print(i)
