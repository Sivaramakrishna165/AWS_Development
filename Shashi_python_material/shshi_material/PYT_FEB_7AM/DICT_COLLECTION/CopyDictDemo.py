#D.keys() -> dict_keys | iterable
#D.values( ) -> dict_values | iterable
#D.items() -> dict_items | [(),()]

#D.copy() -> shallow copy of dict

import copy

s1={"sno":101,"sname":"ramesh"}
print("student : ",s1)

#s2=s1.copy()
#s2=dict(s1)
s2=copy.copy(s1)

print("student : ",s2)

s1['sname']="Suresh"
print("student  s1 : ",s1)
print("student  s2 : ",s2)

