
f=open("data1.txt","w+")
#print("type is : ",type(f))

print("File Name : ",f.name)
print("File Mode  : ",f.mode)

print("Is Readable ? : ",f.readable())
print("Is Writable ? : ",f.writable())

print("Is File Closed ? : ",f.closed)

f.close()
print("Is File Closed ? : ",f.closed)

