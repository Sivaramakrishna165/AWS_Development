
#read( ) -> str

f=open("data2.txt","r")
data=f.read()
print(data)

pos=f.tell()
print("File Pointed @ : ",pos)

f.seek(0)
pos=f.tell()
print("File Pointed @ : ",pos)
print("===================")

data=f.read(6)  #read(bytes) -> str
print(data)


f.close()
