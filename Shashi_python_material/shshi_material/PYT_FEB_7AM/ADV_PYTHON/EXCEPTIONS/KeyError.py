

stu={"sno":101,"sname":"raj","scity":"hyd"}
print("Student : ",stu)

key=input("Enter key : ")

if key in stu.keys():   
    name=stu[key]
    print("Value is : ",name)
else:
    print("Sorry Key is not found")
