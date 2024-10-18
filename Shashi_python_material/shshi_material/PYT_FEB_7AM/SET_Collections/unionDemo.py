#S.union(iterable) -> set vs
#S.update(iterable)

s1={1,2,3}
s2={2,3,4}
print("s1 : ",s1)
print("s2 : ",s2)

s3=s1|s2
print("s1 union s2 : ",s3)

s4=s1.union(s2)
print("s1 union s2 : ",s4)
print("s1 : ",s1)
print("===============")

s1.update(s2) #s1=s1|s2
print("s1 update s2 : ",s1)






