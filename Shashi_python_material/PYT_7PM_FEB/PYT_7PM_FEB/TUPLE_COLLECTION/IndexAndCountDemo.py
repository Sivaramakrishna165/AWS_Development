#     0  1    2   3    4    5
t=(10,20,30,10,50,60)
print("tuple is : ",t)

#t.index(item[,start,end]) -> int
pos=t.index(10)
pos=t.index(10,2,5)
print("Found @ : ",pos)

#t.count(item) -> int
no=t.count(10)
print("Found For : ",no," times ")


