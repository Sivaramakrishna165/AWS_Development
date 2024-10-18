#S.union(iterable) -> set vs
#S.update(iterable)

#S.intersection(iterable) -> set vs
#S.intersection_update(iterable)

#S.difference(iterable) -> set vs
#S.difference_update(iterable)

#S.symmetric_difference(iterable) vs
#S.symmetric_difference_update(iterable)

s1={1,2,3}
s2={2,3,4}
print("s1 : ",s1)
print("s2 : ",s2)

s3=s1^s2
print("s1^s2 : ",s3)
print("s1 : ",s1)
print("=============")

s4=s1.symmetric_difference(s2)
print("s1 symmetric_difference(s2)  ",s4)
print("s1 : ",s1)
print("=====================")

s1.symmetric_difference_update(s2)
print("s1 symmetric_difference_update s2 ")
print("s1 : ",s1)






















