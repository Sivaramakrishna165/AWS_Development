#     0  1    2   3    4    5
t=(10,20,30,40,50,60)
print("tuple is : ",t)

pos=int(input("Enter index pos : ")) #2

if pos<len(t):
    item= int(input("Enter new item : ")),
    f=t[0:pos]
    s=t[pos+1:]
    t=f+item+s
    print("Update : ",t)
else:
    print("Invalid index for update")
    

    

