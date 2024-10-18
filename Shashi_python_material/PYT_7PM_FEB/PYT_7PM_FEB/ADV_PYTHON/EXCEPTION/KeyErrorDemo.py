
stu={"sno":101,"sname":"roja","scity":"kadapa"}
print("student : ",stu)
key=input("Enter key : ") #sname

if key in stu.keys():    
    value=stu[key]
    print("Value is : ",value)
else:
    print("Sorry Key Is Not Found ")
