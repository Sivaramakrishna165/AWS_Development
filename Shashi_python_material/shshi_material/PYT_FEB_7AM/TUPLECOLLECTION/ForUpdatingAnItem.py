#    0    1   2    3   4    5
t=(10,20,30,40,50,60)
print("Data is : ",t)

pos=int(input("Enter Index Pos : "))

if pos<len(t):
    item=[int(input("Enter an item"))]
    f=t[0:pos]
    s=t[pos+1:]
    t=f+tuple(item)+s
    print("After updating : ",t)   
             
else:
    print("Invalid Index ")
