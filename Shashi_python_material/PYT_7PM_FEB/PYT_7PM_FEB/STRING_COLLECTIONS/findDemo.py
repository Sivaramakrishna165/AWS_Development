

#len(iterable) -> int 
#S.find(substr[,start,end]) -> int | -1
s="welcome"
pos=s.find("e")
print("Found @ : ",pos)
print("=================")

pos=s.find("E",3,7)
print("Found @ : ",pos)

#S.rfind(substr[,start,end]) -> int
s1="WELCOME"
pos=s1.rfind("E")
print("found @ : ",pos)

