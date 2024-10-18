'''
Nested Collection is the process of
defining the collection or collections in
another collection.
'''

lst=[10,12.12,[11,22,33],
                          (1.1,2.2,3.3),
                          {"aaa","bbb","ccc"},
                          {"sno":101,"sname":"ramesh"}  ]

print("Inner List : ",lst[2] )
print("2nd item from the inner list : ",lst[2][1])

print("Inner tuple : ",lst[3])
print("Inner Dict : ",lst[5])
print("Sname is : ",lst[5]['sname'])
print("sname is : ",lst[5].get('sname'))

lst[5]['sname']='Suresh'
#lst[5].update({"sname":"suresh"})
print("Dict : ",lst[5])








