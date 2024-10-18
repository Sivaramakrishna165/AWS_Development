#S.union(iterable) -> set vs
#S.update(iterable)

#S.intersection(iterable) -> set vs
#S.intersection_update(iterable)

s1={1,2,3}
s2={2,3,4}
print("s1 : ",s1)
print("s2 : ",s2)

s3=s1&s2
print("s3 : ",s3)

s4=s1.intersection(s2)
print("s1 intersection s2 : ",s4)
print("s1 : ",s1)
print("====================")

s1.intersection_update(s2)  #s1=s1&s2
print("s1 intersection_update s2 : ")
print("Result in s1 : ",s1)














