
'''
for <variable> in <iterable>:
    .... statement(s)

iterable : str | list | tuple | set | dict
                  range | frozenset | OrderedDict
                  dict_keys | dict_values | dict_items
                  map | filter | zip | file | cursor | callable_iterator
'''
import time

lst=[10,20,30]
print("List : ",lst)

for i in lst:
    time.sleep(.2)
    print(i)
print("=================")

t=(10,12.12,None,"James",10+20j)
print("tuple : ",t)

for i in t:
    time.sleep(.2)
    print(i)
print("==================")

s="welcome"
print("String data : ",s)

for i in s:
    time.sleep(.2)
    print(i)
print("=================")

stu={"sno":101,"sname":"ramesh","sage":23}
for i in stu:
    time.sleep(.2)
    print(i)


























    










