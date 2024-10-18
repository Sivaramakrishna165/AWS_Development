
l1=[10,20,30,40]
l2=[20,30,60,70]
print("l1 : ",l1)
print("l2 : ",l2)

#frozenset(iterable) -> FS object
'''
fs1=frozenset(l1)
fs2=frozenset(l2)
fs3=fs1.intersection(fs2)
l3=list(fs3)
print("Result is : ",l3)
'''

print("Result : ",
      list( frozenset(l1).intersection(frozenset(l2))))









