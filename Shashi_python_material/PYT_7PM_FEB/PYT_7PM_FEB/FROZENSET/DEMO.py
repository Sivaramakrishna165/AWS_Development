

'''
set vs frozenset
   - both are work almost same
   - difference is set is mutable where as
                frozenset is immutable.

    - we can create set by using set( ) or set(iterable)
    - we can create frozenset by using frozenset( )
    or frozenset(iterable)

    Note: we can perform only set related operations
    like union | intersection | difference |
    symmetric_difference 
'''

l1=[10,20,30]
l2=[30,40,50]
print("l1 : ",l1)
print("l2 : ",l2)

'''
f1=frozenset(l1)
f2=frozenset(l2)
f3=f1.intersection(f2)
#print("Result is : ",f3)
l3=list(f3) '''


print("Result is : ",
      list(frozenset(l1).intersection(frozenset(l2))))


















