''' Iterables are :
     str | list | tuple | set | dict | range
     cursor | file | dict_keys | dict_values
     dict_items | callable_iterator | map | zip | filter .... '''

''' for <variable> in <iterable>:
    .... stmt(s) '''

import time
t=(10,20,3.2,"Shashi")
print("tuple : ",t)

for i in t:
    time.sleep(.2)
    print(i)

print("============================")

s="WELCOME"
print("String is : ",s)

for i in s:
    time.sleep(.2)
    print(i,end=' ')

print("\n ===============================")

s={"sno":101, "sname":"sai", "scity":"kmm" }
print("dict : ",s)

for i in s:
    time.sleep(.2)
    print(i)






















