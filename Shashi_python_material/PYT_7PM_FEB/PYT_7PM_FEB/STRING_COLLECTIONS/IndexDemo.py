
#len(iterable) -> int 
#S.index(substr[,start,end]) -> int | ValueError
s="welcome"
pos=s.index("e")
print("Found @ : ",pos)
print("=================")

pos=s.index("e",3,7)
print("Found @ : ",pos)

#S.rindex(substr[,start,end]) -> int
s1="WELCOME"
pos=s1.rindex("E")
print("found @ : ",pos)

