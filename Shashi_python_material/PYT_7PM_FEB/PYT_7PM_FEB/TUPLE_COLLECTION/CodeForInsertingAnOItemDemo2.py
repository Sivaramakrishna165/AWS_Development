#     0  1    2   3    4    5
t=(10,20,30,40,50,60)
print("tuple is : ",t)

pos=int(input("Enter index pos : ")) #2

if pos<len(t):
    item=input("Enter new item : "),  #input( )->str
    f=t[0:pos]   #f=(10,20)
    s=t[pos: :]   #s=(30,40,50,60)
    t=f+item+s    
    print("Result is : ",t)
    
else:
    print("Invalid Index For Insert ")
    

