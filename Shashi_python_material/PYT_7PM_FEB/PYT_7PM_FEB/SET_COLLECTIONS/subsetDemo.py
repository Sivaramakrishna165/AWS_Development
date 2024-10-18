
#s.add(item)
#s.copy( ) -> shallow copy

#s.remove(item)  KeyError
#s.discard(item)
#s.clear( )

#S.union(iterable) -> set vs
#S.update(iterable)

#s.intersection(iterable) -> set  vs
#s.intersection_update(iterable)

#s.difference(iterable) -> set vs
#s.difference_update(iterable)

#s.symmetric_difference(iterable) ->set vs
#s.symmetric_difference_update(iterable)

#S.issubset(iterable) -> bool
#S.issuperset(iterable) -> bool

s1={1,2}
s2={1,2,3,4,5}
print("s1 : ",s1)
print("s2 : ",s2)
print("s1 issubset of s2 :", s1.issubset(s2))
print("s2 issuperset of s1 : ",s2.issuperset(s1))



































