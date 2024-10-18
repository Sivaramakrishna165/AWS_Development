#     0  1    2   3    4    5
t=(10,20,30,40,50,60)
print("tuple is : ",t)

pos=int(input("Enter index pos : ")) 

if pos<len(t):
    f=t[0:pos:1]
    s=t[pos+1: :1]
    t=f+s
    print("Result after deleting : ",t)
else:
    print("Sorry Invalid Index ")
    
