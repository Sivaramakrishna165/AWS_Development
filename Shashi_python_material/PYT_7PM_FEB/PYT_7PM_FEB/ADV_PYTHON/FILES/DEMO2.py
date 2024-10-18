
f=open("sample","w+")

print ("Type is : ",type(f))
print ("Filename : ",f.name)
print ("File Mode : ",f.mode)

print ("is File Readable ? : ",f.readable())
print ("is File Writable ? : ",f.writable())

print ("is File Closed  ? : ",f.closed)
f.close( )
print("is File Closed ? : ",f.closed)
