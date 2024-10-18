#    0    1   2    3   4    5
t=(10,20,30,40,50,60)
print("Data is : ",t)

pos=eval(input("Enter index pos : ")) #2

if pos<len(t):
    #item= int(input("Enter an item ")) ,
    #item= [ int( input("Enter an item " ) ) ]
    item=int( input("Enter an item : ") )
    f=t[0:pos]
    s=t[pos: ]
    t=f+(item,)+s 
    print("After Insert : ",t)
else:
    print("Invalid Index ")
