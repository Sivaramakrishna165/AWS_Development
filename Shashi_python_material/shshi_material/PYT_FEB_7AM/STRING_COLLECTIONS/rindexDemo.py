
#s.split([chars]) -> list
#s.lstrip([chars]) -> str
#s.rstrip([chars]) -> str
#s.strip([chars]) -> str

#s.index(sub[,start,end]) -> int  | ValueError   vs 
#s.rindex(sub[,start,end]) -> int

#s.find(sub[,start,end]) -> int | -1
#s.rfind(sub[,start,end]) -> int

s="welcome"
print("data is : ",s)

pos=s.rindex("e")
print("Found @ : ",pos)

pos=s.rindex("e",3,7)
print("Found @ : ",pos)

pos=s.rindex("E",3,7)
print("Found @ : ",pos)











