#read( ) -> str
#read(bytes) -> str

f=open("data3.txt")

if f.mode=="r":
    data=f.read()
    print(data)

pos=f.tell()
print("File Pointed @ : ",pos)

f.seek(0)
pos=f.tell()
print("File Pointed @ : ",pos)

data=f.read(5)
print("Data is : ",data)



f.close()
