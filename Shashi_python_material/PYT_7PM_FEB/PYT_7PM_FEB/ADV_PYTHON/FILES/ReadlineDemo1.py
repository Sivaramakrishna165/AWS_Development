#read( ) -> str
#read(bytes) -> str
#readline( ) -> str

f=open("data3.txt","r")
l1=f.readline()
print(l1)

l2=f.readline()
print(l2)

f.close()
